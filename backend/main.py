from datetime import datetime, timedelta
import logging
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from backend.database import get_db
from backend.models import (
    GapAnalysis,
    JobDescription,
    LearningResource,
    Resume,
    User,
    UserTask,
)
from backend.cache import cache_api_response
from backend.services.llm_service import analyze_gap
from backend.services.llm_service import generate_resume_content, parse_jd, parse_resume
from backend.services.parser_service import extract_text_from_pdf_async

app = FastAPI(title="MatchLearn API")


@app.get("/users/me", response_model=dict)
async def read_users_me(current_user: User = Depends(get_current_user)):
    logging.info(f"DEBUG: Accessing /users/me for {current_user.username}")
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response
class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class JDCreate(BaseModel):
    title: str
    company: Optional[str] = None
    description: str


class GapAnalysisRequest(BaseModel):
    resume_id: int
    jd_id: int
    force_analyze: Optional[bool] = False


class TaskCreate(BaseModel):
    user_id: int
    skill_tag: str
    recommendation: str


class TaskUpdate(BaseModel):
    task_id: int
    status: str


class ResumeUpdateFromTask(BaseModel):
    task_id: int
    resume_id: int


# --- Endpoints ---


@app.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
    }


# Duplicate /users/me removed from here


@app.post("/users", response_model=dict)
async def create_user(user: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user exists
    result = await db.execute(select(User).where(User.username == user.username))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    new_user = User(
        username=user.username, email=user.email, hashed_password=hashed_password
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}


@app.post("/resumes/upload", response_model=dict)
async def upload_resume(
    user_id: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to upload for this user"
        )

    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    # Read file content with size limit
    content = await file.read(10 * 1024 * 1024)  # Limit to 10MB

    # Check if we read the entire file
    if await file.read(1):  # Try to read one more byte
        raise HTTPException(status_code=400, detail="PDF file too large (max 10MB)")

    # Use async PDF parsing
    text = await extract_text_from_pdf_async(content)

    # Parse with LLM
    parsed_json = await parse_resume(text)

    new_resume = Resume(
        user_id=user_id,
        raw_text=text,
        structured_json=parsed_json,
        filename=file.filename,
    )
    db.add(new_resume)
    await db.commit()
    await db.refresh(new_resume)

    return {"id": new_resume.id, "parsed_data": new_resume.structured_json}


@app.get("/resumes/list", response_model=List[dict])
@cache_api_response(ttl=60)  # Cache for 1 minute
async def list_resumes(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Optimized query: only select needed fields
    result = await db.execute(
        select(
            Resume.id,
            Resume.created_at,
            Resume.updated_at,
            Resume.filename,
            Resume.structured_json,
        )
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .limit(100)  # Limit to recent 100 resumes for performance
    )
    resumes = result.all()

    return [
        {
            "id": resume_id,
            "created_at": created_at.isoformat(),
            "name": (
                filename
                if filename
                else (
                    structured_json.get("name", "未命名简历")
                    if isinstance(structured_json, dict)
                    else "未命名简历"
                )
            ),
            "updated_at": updated_at.isoformat() if updated_at else None,
        }
        for resume_id, created_at, updated_at, filename, structured_json in resumes
    ]


@app.post("/jds", response_model=dict)
async def create_jd(
    jd: JDCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Parse with LLM
    parsed_json = await parse_jd(jd.description)

    # Use the title extracted from JD text by LLM, fallback to provided title
    extracted_title = parsed_json.get("title", jd.title)

    new_jd = JobDescription(
        title=extracted_title,
        company=jd.company,
        raw_text=jd.description,
        structured_json=parsed_json,
    )
    db.add(new_jd)
    await db.commit()
    await db.refresh(new_jd)

    return {
        "id": new_jd.id,
        "parsed_data": new_jd.structured_json,
        "extracted_title": extracted_title,
    }


@app.post("/gap-analysis", response_model=dict)
async def perform_gap_analysis(
    request: GapAnalysisRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logging.info(
        f"DEBUG: perform_gap_analysis request for user {current_user.id}, resume {request.resume_id}, jd {request.jd_id}"
    )
    # Optimized query: fetch resume and JD in a single query
    result = await db.execute(
        select(Resume, JobDescription)
        .where(Resume.id == request.resume_id)
        .where(JobDescription.id == request.jd_id)
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Resume or JD not found")

    resume, jd = row

    if resume.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Not authorized to access this resume"
        )

    # Check for cached analysis if not forced
    logging.info("DEBUG: Checking cache...")
    if not request.force_analyze:
        # Optimized query: fetch latest analysis with resume update check
        cached_result = await db.execute(
            select(GapAnalysis)
            .where(GapAnalysis.resume_id == request.resume_id)
            .where(GapAnalysis.job_description_id == request.jd_id)
            .where(
                # Only return cached analysis if resume hasn't been updated since
                (Resume.updated_at.is_(None))
                | (GapAnalysis.created_at >= Resume.updated_at)
            )
            .join(Resume, GapAnalysis.resume_id == Resume.id)
            .order_by(GapAnalysis.created_at.desc())
            .limit(1)
        )
        cached_analysis = cached_result.scalar_one_or_none()

        if cached_analysis:
            return {
                "overall_score": cached_analysis.overall_score,
                "radar_data": cached_analysis.radar_data,
                "gap_details": cached_analysis.gap_details,
                "summary": "Loaded from cache",
            }

    # Check if resume JSON is valid (not an error response)
    if isinstance(resume.structured_json, dict) and "error" in resume.structured_json:
        raise HTTPException(
            status_code=400,
            detail=f"简历解析失败: {resume.structured_json.get('error', '未知错误')}",
        )

    # Check if JD JSON is valid (not an error response)
    if isinstance(jd.structured_json, dict) and "error" in jd.structured_json:
        raise HTTPException(
            status_code=400,
            detail=f"职位描述解析失败: {jd.structured_json.get('error', '未知错误')}",
        )

    # Get user's completed courses with optimized query
    completed_courses_result = await db.execute(
        select(UserTask.skill_tag, LearningResource.title, LearningResource.source)
        .join(LearningResource, UserTask.resource_id == LearningResource.id)
        .where(UserTask.user_id == resume.user_id, UserTask.status == "completed")
        .order_by(UserTask.completed_at.desc())
        .limit(50)  # Limit to recent 50 courses for performance
    )
    completed_courses_db = completed_courses_result.all()

    # Format completed courses
    completed_courses = [
        {
            "skill": skill_tag,
            "course_title": title if title else "Unknown Course",
            "source": source if source else "Unknown",
        }
        for skill_tag, title, source in completed_courses_db
    ]

    logging.info("DEBUG: Calling LLM analyze_gap with completed courses...")            
    # Ensure structured_json is a dictionary
    resume_data: dict = (
        resume.structured_json if isinstance(resume.structured_json, dict) else {}
    )
    jd_data: dict = jd.structured_json if isinstance(jd.structured_json, dict) else {}
    analysis_result = await analyze_gap(resume_data, jd_data, completed_courses)
    logging.info("DEBUG: LLM returned. Keys:", list(analysis_result.keys()))

    new_analysis = GapAnalysis(
        user_id=resume.user_id,
        resume_id=resume.id,
        job_description_id=jd.id,
        overall_score=analysis_result.get("overall_score", 0),
        radar_data=analysis_result.get("radar_data", {}),
        gap_details=analysis_result.get("gap_details", []),
    )
    db.add(new_analysis)
    await db.commit()
    await db.refresh(new_analysis)

    return analysis_result


@app.post("/tasks", response_model=dict)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if task_data.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # 1. Create a Learning Resource dynamically
    resource = LearningResource(
        title=f"Learn {task_data.skill_tag}",
        source="Custom",
        url=f"https://www.bing.com/search?q=learn+{task_data.skill_tag}+site:imooc.com+OR+site:bilibili.com",
        level="Adaptive",
        duration="Flexible",
        tags=[task_data.skill_tag],
    )
    db.add(resource)
    await db.commit()
    await db.refresh(resource)

    # 2. Create User Task
    new_task = UserTask(
        user_id=task_data.user_id,
        resource_id=resource.id,
        status="in_progress",
        skill_tag=task_data.skill_tag,
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    return {"id": new_task.id, "message": "Task created"}


@app.get("/tasks/{user_id}", response_model=List[dict])
async def list_tasks(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(UserTask)
        .where(UserTask.user_id == user_id)
        .order_by(UserTask.created_at.desc())
    )
    tasks = result.scalars().all()

    return [
        {
            "id": t.id,
            "skill": t.skill_tag,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t in tasks
    ]


@app.post("/tasks/complete")
async def complete_task(
    update: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(UserTask, update.task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Type assertion for mypy
    task.status = "completed"  # type: ignore[assignment]
    task.completed_at = datetime.utcnow()  # type: ignore[assignment]

    # Generate resume update suggestion (handle missing resource gracefully)
    suggestion = ""
    if task.resource_id:
        resource = await db.get(LearningResource, task.resource_id)
        if resource:
            suggestion = await generate_resume_content(
                task_description=f"Completed {resource.title} to improve {task.skill_tag}",
                course_title=str(resource.title) if resource.title else "",
            )
        else:
            # Fallback if resource not found
            suggestion = await generate_resume_content(
                task_description=f"Completed learning task to improve {task.skill_tag}",
                course_title=f"Skill improvement in {task.skill_tag}",
            )
    else:
        # No resource_id, generate generic suggestion
        suggestion = await generate_resume_content(
            task_description=f"Completed learning task to improve {task.skill_tag}",
            course_title=f"Skill improvement in {str(task.skill_tag) if task.skill_tag else 'unknown skill'}",
        )

    task.auto_fill_content = suggestion  # type: ignore[assignment]

    # Get user's latest resume
    resume_result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    latest_resume = resume_result.scalar_one_or_none()

    # Get user's latest job description
    jd_result = await db.execute(
        select(JobDescription).order_by(JobDescription.created_at.desc()).limit(1)
    )
    latest_jd = jd_result.scalar_one_or_none()

    # Update resume with the new content if we have a resume
    if latest_resume:
        # Ensure structured_json is a dictionary
        resume_data: dict = (
            latest_resume.structured_json
            if isinstance(latest_resume.structured_json, dict)
            else {}
        )
        current_json = dict(resume_data)  # Ensure it's a dict copy
        if "projects" not in current_json:
            current_json["projects"] = []

        current_json["projects"].append(
            {
                "name": f"Learning Project: {str(task.skill_tag) if task.skill_tag else 'unknown skill'}",
                "description": (
                    str(task.auto_fill_content) if task.auto_fill_content else ""
                ),
                "technologies": [
                    str(task.skill_tag) if task.skill_tag else "unknown skill"
                ],
            }
        )

        # Update resume
        latest_resume.structured_json = current_json  # type: ignore[assignment]
        latest_resume.updated_at = datetime.utcnow()  # type: ignore[assignment]

        # Flag modified for JSON field
        from sqlalchemy.orm.attributes import flag_modified

        flag_modified(latest_resume, "structured_json")

    await db.commit()

    # Perform gap analysis if we have both resume and JD
    analysis_result = None
    if latest_resume and latest_jd:
        # Get completed courses for this analysis
        completed_courses_result = await db.execute(
            select(UserTask, LearningResource)
            .join(LearningResource, UserTask.resource_id == LearningResource.id)
            .where(
                UserTask.user_id == current_user.id,
                UserTask.status == "completed",
                UserTask.completed_at.is_not(None),
                UserTask.completed_at <= datetime.utcnow(),
            )
            .order_by(UserTask.completed_at.desc())
        )
        completed_courses_db = completed_courses_result.all()

        # Format completed courses
        completed_courses = []
        for course in completed_courses_db:
            completed_courses.append(
                {
                    "skill": course.UserTask.skill_tag,
                    "course_title": (
                        course.LearningResource.title
                        if course.LearningResource
                        else "Unknown Course"
                    ),
                    "source": (
                        course.LearningResource.source
                        if course.LearningResource
                        else "Unknown"
                    ),
                }
            )

        # Ensure structured_json is a dictionary
        resume_data_for_analysis: dict = (
            latest_resume.structured_json
            if isinstance(latest_resume.structured_json, dict)
            else {}
        )
        jd_data: dict = (
            latest_jd.structured_json
            if isinstance(latest_jd.structured_json, dict)
            else {}
        )

        # Perform gap analysis
        analysis_result = await analyze_gap(
            resume_data_for_analysis, jd_data, completed_courses
        )

        # Save the analysis to database
        new_analysis = GapAnalysis(
            user_id=current_user.id,
            resume_id=latest_resume.id,
            job_description_id=latest_jd.id,
            overall_score=analysis_result.get("overall_score", 0),
            radar_data=analysis_result.get("radar_data", {}),
            gap_details=analysis_result.get("gap_details", []),
        )
        db.add(new_analysis)
        await db.commit()
        await db.refresh(new_analysis)

    return {
        "message": "Task completed and resume updated",
        "resume_suggestion": suggestion,
        "resume_updated": latest_resume is not None,
        "gap_analysis_performed": analysis_result is not None,
        "gap_analysis_result": analysis_result,
    }


@app.post("/resumes/update-from-task")
async def update_resume_from_task(
    update: ResumeUpdateFromTask,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = await db.get(UserTask, update.task_id)
    resume = await db.get(Resume, update.resume_id)

    if not task or not resume:
        raise HTTPException(status_code=404, detail="Task or Resume not found")

    if task.user_id != current_user.id or resume.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not task.auto_fill_content:
        raise HTTPException(status_code=400, detail="No content to update")

    # Simple append logic for now (in real app, use LLM to merge intelligently)
    # Ensure structured_json is a dictionary
    resume_data: dict = (
        resume.structured_json if isinstance(resume.structured_json, dict) else {}
    )
    current_json = dict(resume_data)  # Ensure it's a dict copy
    if "projects" not in current_json:
        current_json["projects"] = []

    current_json["projects"].append(
        {
            "name": f"Learning Project: {str(task.skill_tag) if task.skill_tag else 'unknown skill'}",
            "description": (
                str(task.auto_fill_content) if task.auto_fill_content else ""
            ),
            "technologies": [
                str(task.skill_tag) if task.skill_tag else "unknown skill"
            ],
        }
    )

    # Re-assign to trigger SQLAlchemy update detection for JSON fields
    resume.structured_json = current_json  # type: ignore[assignment]
    task.status = "verified"  # type: ignore[assignment]

    # Explicitly flag modified if needed, though reassignment usually works
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(resume, "structured_json")

    await db.commit()
    await db.refresh(resume)

    return {
        "message": "Resume updated successfully",
        "new_resume_data": resume.structured_json,
    }


@app.get("/resumes/{user_id}", response_model=dict)
async def get_latest_resume(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Get the latest resume for the user
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == user_id)
        .order_by(Resume.created_at.desc())
        .limit(1)
    )
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    # Return structured_json but inject the resume ID
    response_data = dict(resume.structured_json)
    response_data["id"] = resume.id
    return response_data


@app.get("/history", response_model=List[dict])
async def get_analysis_history(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    # Get all gap analyses for the current user
    result = await db.execute(
        select(GapAnalysis, JobDescription)
        .join(JobDescription, GapAnalysis.job_description_id == JobDescription.id)
        .where(GapAnalysis.user_id == current_user.id)
        .order_by(GapAnalysis.created_at.desc())
    )
    history = result.all()
    logging.info("DEBUG: history count:", len(history))
    history_with_courses = []
    completed_courses_result1 = await db.execute(
            select(UserTask, LearningResource)
            .join(LearningResource, UserTask.resource_id == LearningResource.id))
    completed_courses1 = completed_courses_result1.all()
    logging.info("DEBUG: completed_courses1 count:", completed_courses1)

    for analysis in history:
        # Get completed courses that were completed BEFORE this analysis
        completed_courses_result = await db.execute(
            select(UserTask, LearningResource)
            .join(LearningResource, UserTask.resource_id == LearningResource.id)
            .where(
                UserTask.user_id == current_user.id,
                UserTask.status.in_(["completed", "verified"]),
                UserTask.completed_at.is_not(None),  # Must have completion date
                # Only include courses completed before or at the analysis time
                UserTask.completed_at <= analysis.GapAnalysis.created_at,
            )
            .order_by(UserTask.completed_at.desc())
        )
        completed_courses = completed_courses_result.all()

        # Format completed courses
        formatted_courses = []
        for course in completed_courses:
            formatted_courses.append(
                {
                    "skill": course.UserTask.skill_tag,
                    "course_title": (
                        course.LearningResource.title
                        if course.LearningResource
                        else "Unknown Course"
                    ),
                    "completed_at": (
                        course.UserTask.completed_at.isoformat()
                        if course.UserTask.completed_at
                        else None
                    ),
                    "source": (
                        course.LearningResource.source
                        if course.LearningResource
                        else "Unknown"
                    ),
                }
            )

        history_with_courses.append(
            {
                "id": analysis.GapAnalysis.id,
                "resume_id": analysis.GapAnalysis.resume_id,
                "jd_id": analysis.GapAnalysis.job_description_id,
                "date": analysis.GapAnalysis.created_at.isoformat(),
                "overall_score": analysis.GapAnalysis.overall_score,
                "radar_data": analysis.GapAnalysis.radar_data,
                "job_title": analysis.JobDescription.title,
                "gap_details": analysis.GapAnalysis.gap_details,
                "completed_courses": formatted_courses,
            }
        )

    return history_with_courses


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
