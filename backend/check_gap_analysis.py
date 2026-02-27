import asyncio
import os
import sys
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import engine
from backend.models import GapAnalysis


async def check_gap_analysis():
    async with AsyncSession(engine) as session:
        # 检查所有GapAnalysis记录
        result = await session.execute(select(GapAnalysis))
        analyses = result.scalars().all()

        logging.info(f"数据库中的GapAnalysis记录总数: {len(analyses)}")

        if len(analyses) == 0:
            logging.warning("警告: 数据库中没有找到任何GapAnalysis记录!")
            logging.warning("这意味着用户从未执行过技能差距分析。")
        else:
            logging.info(f"找到 {len(analyses)} 条分析记录:")   
            for i, analysis in enumerate(analyses[:10]):  # 只显示前10条
                logging.info(f"记录 {i+1}:")
                logging.info(f"  ID: {analysis.id}")
                logging.info(f"  用户ID: {analysis.user_id}")
                logging.info(f"  简历ID: {analysis.resume_id}")
                logging.info(f"  JD_ID: {analysis.job_description_id}")
                logging.info(f"  创建时间: {analysis.created_at}")
                logging.info(f"  总体分数: {analysis.overall_score}")
                logging.info(
                    f"  技能差距数量: {len(analysis.gap_details) if analysis.gap_details else 0}"
                )
                logging.info("")


if __name__ == "__main__":
    asyncio.run(check_gap_analysis())
