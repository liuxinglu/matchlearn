import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from sqlalchemy.future import select

from backend.database import AsyncSessionLocal
from backend.models import (
    GapAnalysis,
    JobDescription,
    LearningResource,
    Resume,
    User,
    UserTask,
)

logging.info("=== Testing History Data ===")


async def test_history():
    async with AsyncSessionLocal() as session:
        logging.info("\n=== 1. 检查用户 ===")
        result = await session.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        logging.info(f"用户存在: {user is not None}")
        if user:
            logging.info(f"用户ID: {user.id}, 用户名: {user.username}")

        logging.info("\n=== 2. 检查GapAnalysis ===")
        result = await session.execute(
            select(GapAnalysis, JobDescription)
            .join(JobDescription, GapAnalysis.job_description_id == JobDescription.id)
            .where(GapAnalysis.user_id == 1)
            .order_by(GapAnalysis.created_at.desc())
        )
        history = result.all()
        logging.info(f"Gap分析数量: {len(history)}")

        if len(history) == 0:
            logging.info("警告: 用户还没有进行过任何gap分析!")
            logging.info("用户需要先上传简历和JD，然后点击分析按钮。")

        for i, analysis in enumerate(history):
            logging.info(f"\n--- 分析记录 {i+1} ---")
            logging.info(f"分析ID: {analysis.GapAnalysis.id}")
            print(f"创建时间: {analysis.GapAnalysis.created_at}")
            print(f"职位标题: {analysis.JobDescription.title}")

        logging.info("\n=== 3. 检查UserTask (学习任务) ===")
        result = await session.execute(select(UserTask).where(UserTask.user_id == 1))
        tasks = result.scalars().all()
        logging.info(f"用户任务数量: {len(tasks)}")

        for i, task in enumerate(tasks):
            logging.info(f"\n任务 {i+1}:")
            logging.info(f"  任务ID: {task.id}")
            logging.info(f"  技能标签: {task.skill_tag}")
            logging.info(f"  状态: {task.status}")
            logging.info(f"  创建时间: {task.created_at}")
            logging.info(f"  完成时间: {task.completed_at}")
            logging.info(f"  资源ID: {task.resource_id}")

        logging.info("\n=== 4. 检查LearningResource (学习资源) ===")
        result = await session.execute(select(LearningResource))
        resources = result.scalars().all()
        logging.info(f"学习资源数量: {len(resources)}")

        for i, resource in enumerate(resources):
            logging.info(f"\n资源 {i+1}:")
            logging.info(f"  资源ID: {resource.id}")
            logging.info(f"  标题: {resource.title}")
            logging.info(f"  来源: {resource.source}")
            logging.info(f"  URL: {resource.url}")

        logging.info("\n=== 5. 检查已完成的课程 (JOIN查询) ===")
        completed_courses_result = await session.execute(
            select(UserTask, LearningResource)
            .join(LearningResource, UserTask.resource_id == LearningResource.id)
            .where(UserTask.user_id == 1, UserTask.status == "completed")
            .order_by(UserTask.completed_at.desc())
        )
        completed_courses = completed_courses_result.all()
        logging.info(f"已完成的课程数量: {len(completed_courses)}")

        if len(completed_courses) == 0:
            logging.warning("警告: 没有找到已完成的课程!")
            logging.warning("可能的原因:")
            logging.warning("  1. UserTask表中没有status='completed'的记录")
            logging.warning("  2. UserTask.resource_id没有对应的LearningResource记录")
            logging.warning("  3. JOIN查询失败")

        for j, course in enumerate(completed_courses):
            logging.info(f"\n课程 {j+1}:")
            logging.info(f"  技能: {course.UserTask.skill_tag}")
            logging.info(
                f"  标题: {course.LearningResource.title if course.LearningResource else 'Unknown'}"
            )
            logging.info(
                f"  来源: {course.LearningResource.source if course.LearningResource else 'Unknown'}"
            )
            logging.info(f"  完成时间: {course.UserTask.completed_at}")


if __name__ == "__main__":
    asyncio.run(test_history())
