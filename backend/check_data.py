import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select

from backend.database import AsyncSessionLocal
from backend.models import GapAnalysis, UserTask


async def check_data():
    async with AsyncSessionLocal() as session:
        # Check UserTask
        result = await session.execute(select(UserTask).where(UserTask.user_id == 1))
        tasks = result.scalars().all()
        print(f"Found {len(tasks)} UserTasks for user 1:")
        for task in tasks:
            print(
                f"  - ID: {task.id}, Skill: {task.skill_tag}, Status: {task.status}, Completed: {task.completed_at}"
            )

        # Check GapAnalysis
        result = await session.execute(
            select(GapAnalysis).where(GapAnalysis.user_id == 1)
        )
        analyses = result.scalars().all()
        print(f"\nFound {len(analyses)} GapAnalyses for user 1:")
        for analysis in analyses:
            print(f"  - ID: {analysis.id}, Created: {analysis.created_at}")


if __name__ == "__main__":
    asyncio.run(check_data())
