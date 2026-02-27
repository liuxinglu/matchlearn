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


async def check_latest_data():
    async with AsyncSessionLocal() as session:
        print("=== 检查最新数据状态 ===")

        print("\n1. 检查用户")
        result = await session.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()
        print(f"用户存在: {user is not None}")
        if user:
            print(f"用户ID: {user.id}, 用户名: {user.username}")

        print("\n2. 检查最新的GapAnalysis")
        result = await session.execute(
            select(GapAnalysis, JobDescription, Resume)
            .join(JobDescription, GapAnalysis.job_description_id == JobDescription.id)
            .join(Resume, GapAnalysis.resume_id == Resume.id)
            .where(GapAnalysis.user_id == 1)
            .order_by(GapAnalysis.created_at.desc())
        )
        analyses = result.all()
        logging.info(f"Gap分析总数: {len(analyses)}")

        if len(analyses) > 0:
            latest_analysis = analyses[0]
            logging.info(f"\n最新分析记录:")
            logging.info(f"  分析ID: {latest_analysis.GapAnalysis.id}")
            logging.info(f"  创建时间: {latest_analysis.GapAnalysis.created_at}")
            logging.info(f"  职位标题: {latest_analysis.JobDescription.title}")
            logging.info(f"  简历ID: {latest_analysis.Resume.id}")
            logging.info(f"  总体分数: {latest_analysis.GapAnalysis.overall_score}")
        else:
            logging.warning("警告: 没有找到任何分析记录!")

        result = await session.execute(
            select(UserTask, LearningResource)
            .join(
                LearningResource,
                UserTask.resource_id == LearningResource.id,
                isouter=True,
            )
            .where(UserTask.user_id == 1)
            .order_by(UserTask.created_at.desc())
        )
        tasks = result.all()
        print(f"用户任务总数: {len(tasks)}")

        for i, task in enumerate(tasks):
            print(f"\n任务 {i+1}:")
            print(f"  任务ID: {task.UserTask.id}")
            print(f"  技能标签: {task.UserTask.skill_tag}")
            print(f"  状态: {task.UserTask.status}")
            print(f"  创建时间: {task.UserTask.created_at}")
            print(f"  完成时间: {task.UserTask.completed_at}")
            if task.LearningResource:
                print(f"  课程标题: {task.LearningResource.title}")
                print(f"  课程来源: {task.LearningResource.source}")
            else:
                print(f"  课程资源: 未关联")

        print("\n4. 检查已完成的课程 (status='completed')")
        completed_tasks = [t for t in tasks if t.UserTask.status == "completed"]
        print(f"已完成的课程数量: {len(completed_tasks)}")

        for i, task in enumerate(completed_tasks):
            print(f"\n已完成课程 {i+1}:")
            print(f"  技能: {task.UserTask.skill_tag}")
            if task.LearningResource:
                print(f"  课程: {task.LearningResource.title}")
                print(f"  来源: {task.LearningResource.source}")
            print(f"  完成时间: {task.UserTask.completed_at}")

        print("\n5. 模拟历史记录查询")
        if len(analyses) > 0:
            for i, analysis in enumerate(analyses[:3]):  # 只检查前3个分析
                print(f"\n--- 分析记录 {i+1} (ID: {analysis.GapAnalysis.id}) ---")
                print(f"分析时间: {analysis.GapAnalysis.created_at}")

                # 模拟历史记录查询逻辑
                completed_courses_result = await session.execute(
                    select(UserTask, LearningResource)
                    .join(
                        LearningResource,
                        UserTask.resource_id == LearningResource.id,
                        isouter=True,
                    )
                    .where(UserTask.user_id == 1, UserTask.status == "completed")
                    .order_by(UserTask.completed_at.desc())
                )
                completed_courses = completed_courses_result.all()
                print(f"查询到的已完成课程: {len(completed_courses)}")

                if len(completed_courses) == 0:
                    print("问题: 查询返回0个已完成课程!")
                    print("可能的原因:")
                    print("  1. UserTask.status != 'completed'")
                    print("  2. JOIN条件不匹配")
                    print("  3. 确实没有已完成的课程")
                else:
                    for j, course in enumerate(completed_courses[:3]):  # 只显示前3个
                        print(
                            f"  课程 {j+1}: {course.UserTask.skill_tag} - {course.LearningResource.title if course.LearningResource else '无标题'}"
                        )


if __name__ == "__main__":
    asyncio.run(check_latest_data())
