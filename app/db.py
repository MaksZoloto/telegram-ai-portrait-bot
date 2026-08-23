from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import BigInteger, DateTime, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    language: Mapped[str] = mapped_column(String(5), default="ru")
    credits: Mapped[int] = mapped_column(Integer, default=0)
    generations_used: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


settings = get_settings()
if settings.database_url.startswith("sqlite"):
    Path("data/runtime").mkdir(parents=True, exist_ok=True)

engine: AsyncEngine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_or_create_account(
    session: AsyncSession,
    *,
    telegram_id: int,
    language: str | None = None,
) -> UserAccount:
    account = await session.scalar(select(UserAccount).where(UserAccount.telegram_id == telegram_id))
    if account is None:
        account = UserAccount(
            telegram_id=telegram_id,
            language=language or "ru",
            credits=get_settings().starter_credits,
        )
        session.add(account)
        await session.commit()
        await session.refresh(account)
    elif language and account.language != language:
        account.language = language
        await session.commit()
    return account
