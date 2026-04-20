from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.core.config import settings
from backend.models.media import Base

engine = create_async_engine(str(settings.DATABASE_URL), echo=settings.DEBUG)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False,
)

async def init_db():
    # Importa todos os modelos para garantir que as tabelas são criadas
    from backend.models.media import MediaFile
    from backend.models.timeline import TimelineEvent, Person
    from backend.models.narrative import Story
    from backend.models.video import VideoOutput

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
