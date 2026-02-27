import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from sqlalchemy.future import select

from backend.database import AsyncSessionLocal
from backend.models import LearningResource, UserTask


async def create_test_data():
    async with AsyncSessionLocal() as session:
        # Check if learning resource exists
        result = await session.execute(
            select(LearningResource).where(LearningResource.title == "Python入门课程")
        )
        resource = result.scalar_one_or_none()

        if not resource:
            print("Creating test learning resource...")
            resource = LearningResource(
                title="Python入门课程",
                source="Bilibili",
                url="https://www.bilibili.com/video/BV1qW4y1a7fU",
                level="Entry",
                duration="10h",
                tags=["Python", "Programming"],
            )
            session.add(resource)
            await session.commit()
            await session.refresh(resource)
            print(f"Created resource with ID: {resource.id}")
        else:
            print(f"Resource already exists with ID: {resource.id}")

        # Check if user task exists
        result = await session.execute(
            select(UserTask).where(UserTask.skill_tag == "Python")
        )
        task = result.scalar_one_or_none()

        if not task:
            print("Creating completed task for Python...")
            task = UserTask(
                user_id=1,
                resource_id=resource.id,
                skill_tag="Python",
                status="completed",
                completed_at=datetime.utcnow(),
            )
            session.add(task)
            await session.commit()
            print("Created completed task for Python")
        else:
            print("Task already exists")


if __name__ == "__main__":
    asyncio.run(create_test_data())
