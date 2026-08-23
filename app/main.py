from __future__ import annotations

import asyncio

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import get_settings
from app.db import init_db
from app.handlers.bot import router
from app.web import app


async def run_bot() -> None:
    settings = get_settings()
    if not settings.run_bot:
        return
    if settings.bot_token is None:
        raise RuntimeError("BOT_TOKEN is required when RUN_BOT=true")

    bot = Bot(settings.bot_token.get_secret_value())
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dispatcher.start_polling(bot)


async def run_api() -> None:
    settings = get_settings()
    server = uvicorn.Server(
        uvicorn.Config(app, host=settings.host, port=settings.port, log_level="info")
    )
    await server.serve()


async def main() -> None:
    await init_db()
    if get_settings().run_bot:
        await asyncio.gather(run_api(), run_bot())
    else:
        await run_api()


if __name__ == "__main__":
    asyncio.run(main())
