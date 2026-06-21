"""
Safe migration: creates any missing tables without dropping existing data.
Run this instead of init_db.py when the DB already has supplier data.
"""
import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.db.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def migrate():
    logger.info("Running safe migration — creating missing tables only")
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        # create_all with checkfirst=True only adds tables that don't exist
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    logger.info("Migration complete — all tables are up to date")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())
