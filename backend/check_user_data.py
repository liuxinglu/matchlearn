import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import engine
from backend.models import JobDescription, LearningResource, Resume, User, UserTask


async def check_user_data():
    async with AsyncSession(engine) as session:
        # 检查用户
        user_result = await session.execute(
            select(User).where(User.username == "student_demo")
        )
        user = user_result.scalar_one_or_none()

        if not user:
            logging.error("错误: 找不到用户 student_demo")
            return

        logging.info(f"用户: {user.username} (ID: {user.id})")
        logging.info("")

        # 检查用户的简历
        resume_result = await session.execute(
            select(Resume).where(Resume.user_id == user.id)
        )
        resumes = resume_result.scalars().all()

        logging.info(f"用户的简历数量: {len(resumes)}")
        for i, resume in enumerate(resumes):
            logging.info(f"简历 {i+1}:")
            logging.info(f"  ID: {resume.id}")
            logging.info(f"  文件名: {resume.filename}")
            logging.info(f"  创建时间: {resume.created_at}")
            logging.info(f"  更新时间: {resume.updated_at}")
            logging.info(f"  结构化JSON类型: {type(resume.structured_json)}")
            if isinstance(resume.structured_json, dict):
                logging.info(f"  结构化JSON键: {list(resume.structured_json.keys())[:5]}...")
            logging.info("")

        # 检查用户的JD
        jd_result = await session.execute(
            select(JobDescription).where(JobDescription.user_id == user.id)
        )
        jds = jd_result.scalars().all()

        logging.info(f"用户的JD数量: {len(jds)}")
        for i, jd in enumerate(jds):
            logging.info(f"JD {i+1}:")
            logging.info(f"  ID: {jd.id}")
            logging.info(f"  标题: {jd.title}")
            logging.info(f"  公司: {jd.company}")
            logging.info(f"  创建时间: {jd.created_at}")
            logging.info(f"  结构化JSON类型: {type(jd.structured_json)}")
            if isinstance(jd.structured_json, dict):
                logging.info(f"  结构化JSON键: {list(jd.structured_json.keys())[:5]}...")
            logging.info("")

        # 检查用户的任务
        task_result = await session.execute(
            select(UserTask, LearningResource)
            .join(LearningResource, UserTask.resource_id == LearningResource.id)
            .where(UserTask.user_id == user.id)
        )
        tasks = task_result.all()

        logging.info(f"用户的任务数量: {len(tasks)}")
        for i, (task, resource) in enumerate(tasks):
            print(f"任务 {i+1}:")
            print(f"  任务ID: {task.id}")
            print(f"  技能标签: {task.skill_tag}")
            print(f"  状态: {task.status}")
            print(f"  创建时间: {task.created_at}")
            logging.info(f"  完成时间: {task.completed_at}")
            logging.info(f"  资源标题: {resource.title if resource else '无'}")
            logging.info(f"  资源来源: {resource.source if resource else '无'}")
            logging.info("")


if __name__ == "__main__":
    asyncio.run(check_user_data())
