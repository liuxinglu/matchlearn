import asyncio
import json
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

from backend.cache import cache_llm_result
from backend.prompts import (
    ANALYZE_GAP_PROMPT,
    GENERATE_RESUME_CONTENT_PROMPT,
    PARSE_JD_PROMPT,
    PARSE_RESUME_PROMPT,
)

load_dotenv()

API_KEY = os.getenv("DEEPSEEK_API_KEY")
BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")

if not API_KEY:
    raise ValueError("DEEPSEEK_API_KEY is not set in the environment variables.")

client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)


@cache_llm_result
async def parse_resume(resume_text: str) -> dict:
    """
    Parses resume text into structured JSON using DeepSeek.
    """
    prompt = PARSE_RESUME_PROMPT.format(resume_text=resume_text)

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that parses resumes into JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content is None:
            return {"error": "API返回空内容"}
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return {
            "error": f"JSON格式错误（第{e.lineno}行第{e.colno}列字符{e.pos}处{e.msg}）。请修复简历文件格式，确保JSON结构完整。"
        }
    except Exception as e:
        print(f"简历解析错误: {e}")
        return {"error": f"简历解析失败: {str(e)}"}


@cache_llm_result
async def parse_jd(jd_text: str) -> dict:
    """
    Parses Job Description text into structured JSON using DeepSeek.
    """
    prompt = PARSE_JD_PROMPT.format(jd_text=jd_text)

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that parses Job Descriptions into JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        if content is None:
            return {"error": "API返回空内容"}
        return json.loads(content)
    except json.JSONDecodeError as e:
        print(f"JD JSON解析错误: {e}")
        return {
            "error": f"JD JSON格式错误（第{e.lineno}行第{e.colno}列字符{e.pos}处{e.msg}）。请修复职位描述文件格式，确保JSON结构完整。"
        }
    except Exception as e:
        print(f"职位描述解析错误: {e}")
        return {"error": f"职位描述解析失败: {str(e)}"}


@cache_llm_result
async def analyze_gap(
    resume_json: dict, jd_json: dict, completed_courses: list | None = None
) -> dict:
    """
    Analyzes the gap between a resume and a JD using DeepSeek.
    completed_courses: List of completed courses with format [{"skill": "Python", "course_title": "Python入门", ...}]
    """
    # Check if input data is valid (not error responses)
    if isinstance(resume_json, dict) and "error" in resume_json:
        # Return a proper error response instead of trying to analyze
        return {
            "overall_score": 0,
            "radar_data": {},
            "gap_details": [
                {
                    "missing_skill": "简历数据不完整",
                    "importance": "高",
                    "recommendation": resume_json.get(
                        "error", "简历解析失败，请检查简历文件格式"
                    ),
                    "recommendation_type": "course",
                }
            ],
            "summary": "简历解析失败，无法进行技能匹配分析",
        }

    if isinstance(jd_json, dict) and "error" in jd_json:
        # Return a proper error response instead of trying to analyze
        return {
            "overall_score": 0,
            "radar_data": {},
            "gap_details": [
                {
                    "missing_skill": "职位描述数据不完整",
                    "importance": "高",
                    "recommendation": jd_json.get(
                        "error", "职位描述解析失败，请检查JD文件格式"
                    ),
                    "recommendation_type": "course",
                }
            ],
            "summary": "职位描述解析失败，无法进行技能匹配分析",
        }

    # Format completed courses for the prompt
    completed_courses_text = ""
    if completed_courses and len(completed_courses) > 0:
        completed_courses_text = "\n\n用户已完成的课程：\n"
        for course in completed_courses:
            skill = course.get("skill", "未知技能")
            title = course.get("course_title", "未知课程")
            source = course.get("source", "未知")
            completed_courses_text += f"- {skill}: {title} (来源: {source})\n"

    prompt = ANALYZE_GAP_PROMPT.format(
        resume_json=json.dumps(resume_json, ensure_ascii=False),
        jd_json=json.dumps(jd_json, ensure_ascii=False),
        completed_courses=completed_courses_text,
    )

    try:
        print("DEBUG: analyze_gap start")
        print(
            "DEBUG: resume_json keys:",
            (
                list(resume_json.keys())
                if isinstance(resume_json, dict)
                else type(resume_json)
            ),
        )
        print(
            "DEBUG: jd_json keys:",
            list(jd_json.keys()) if isinstance(jd_json, dict) else type(jd_json),
        )
        print("DEBUG: prompt length:", len(prompt))
        print("DEBUG: calling DeepSeek chat...")
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful career coach assistant.",
                    },
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
            ),
            timeout=60,
        )
        print("DEBUG: DeepSeek response received")
        print(
            "DEBUG: choices count:",
            len(response.choices) if hasattr(response, "choices") else "n/a",
        )
        content = response.choices[0].message.content
        print("DEBUG: content length:", len(content) if content else 0)
        if content is None:
            return {"error": "API返回空内容"}
        return json.loads(content)
    except Exception as e:
        print("ERROR: analyze_gap exception:", e)
        return {"error": str(e)}


@cache_llm_result
async def generate_resume_content(task_description: str, course_title: str) -> str:
    """
    Generates a resume bullet point after completing a learning task.
    """
    prompt = GENERATE_RESUME_CONTENT_PROMPT.format(
        task_description=task_description, course_title=course_title
    )

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional resume writer."},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            return "API返回空内容"
        return content.strip()
    except Exception as e:
        print(f"Error generating resume content: {e}")
        return "Error generating content."
