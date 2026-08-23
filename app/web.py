from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.db import SessionFactory, get_or_create_account, init_db

app = FastAPI(title="AI Portrait Bot Demo API", version="0.1.0")


@app.on_event("startup")
async def startup() -> None:
    await init_db()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "mode": "demo" if get_settings().demo_mode else "leonardo"}


@app.get("/demo-credits", response_class=HTMLResponse)
async def add_demo_credits(
    telegram_id: int = Query(gt=0),
    credits: int = Query(default=10, ge=1, le=100),
) -> str:
    if not get_settings().demo_mode:
        raise HTTPException(status_code=404, detail="Demo credits are disabled")

    async with SessionFactory() as session:
        account = await get_or_create_account(session, telegram_id=telegram_id)
        account.credits += credits
        await session.commit()
        total = account.credits

    return f'''
    <!doctype html>
    <html lang="ru">
      <meta charset="utf-8">
      <title>Demo credits</title>
      <body style="font-family:system-ui;max-width:720px;margin:60px auto">
        <h1>Демо-баланс пополнен</h1>
        <p>Добавлено генераций: <b>{credits}</b></p>
        <p>Текущий баланс: <b>{total}</b></p>
        <p>Вернитесь в Telegram.</p>
      </body>
    </html>
    '''
