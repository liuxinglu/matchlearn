import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select

from backend.database import AsyncSessionLocal, engine
from backend.models import User


async def create_default_user():
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Check if user exists
            result = await session.execute(select(User).where(User.id == 1))
            user = result.scalar_one_or_none()

            if not user:
                print("Creating default user (ID=1)...")
                default_user = User(
                    id=1,
                    username="student_demo",
                    email="student@example.com",
                    hashed_password="hashed_secret_password",
                )
                session.add(default_user)
                print("Default user created successfully!")
            else:
                print("Default user already exists.")


if __name__ == "__main__":
    asyncio.run(create_default_user())
