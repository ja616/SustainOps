import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.db.models import Base, User
from app.db.session import AsyncSessionLocal
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    logger.info("Creating database tables")
    engine = create_async_engine(settings.DATABASE_URL)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Creating superuser")
    async with AsyncSessionLocal() as session:
        user = User(
            email="admin@sustainiq.com",
            hashed_password=get_password_hash("admin"),
            full_name="Admin User",
            is_active=True
        )
        session.add(user)
        await session.commit()
    
    logger.info("Database initialized successfully")

if __name__ == "__main__":
    asyncio.run(init_db())
