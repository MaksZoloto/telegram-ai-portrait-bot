from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.parse import urlencode

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionFactory, UserAccount, get_or_create_account
from app.services.generator import build_generator
from app.styles import STYLES, style_title

router = Router()


class PortraitFlow(StatesGroup):
    waiting_photo = State()
    waiting_style = State()


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
                InlineKeyboardButton(text="English", callback_data="lang:en"),
            ]
        ]
    )


def style_keyboard(language: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=style_title(code, language), callback_data=f"style:{code}")]
            for code in STYLES
        ]
    )


async def account_for(user_id: int) -> UserAccount:
    async with SessionFactory() as session:
        return await get_or_create_account(session, telegram_id=user_id)


@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Выберите язык / Choose language",
        reply_markup=language_keyboard(),
    )


@router.callback_query(F.data.startswith("lang:"))
async def select_language(callback: CallbackQuery, state: FSMContext) -> None:
    language = callback.data.split(":", 1)[1]
    async with SessionFactory() as session:
        account = await get_or_create_account(
            session,
            telegram_id=callback.from_user.id,
            language=language,
        )
    await state.update_data(language=language)
    await state.set_state(PortraitFlow.waiting_photo)
    await callback.answer()
    text = (
        f"Отправьте портретное фото. Доступно генераций: {account.credits}"
        if language == "ru"
        else f"Send a portrait photo. Available generations: {account.credits}"
    )
    await callback.message.answer(text)


@router.message(Command("balance"))
async def balance(message: Message) -> None:
    account = await account_for(message.from_user.id)
    await message.answer(
        f"Credits: {account.credits}\nGenerations used: {account.generations_used}"
    )


@router.message(Command("buy"))
async def buy(message: Message) -> None:
    settings = get_settings()
    query = urlencode({"telegram_id": message.from_user.id, "credits": 10})
    await message.answer(
        "Demo package: 10 generations",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Add demo credits",
                        url=f"{settings.public_base_url.rstrip('/')}/demo-credits?{query}",
                    )
                ]
            ]
        ),
    )


@router.message(PortraitFlow.waiting_photo, F.photo)
async def receive_photo(message: Message, state: FSMContext) -> None:
    photo = message.photo[-1]
    telegram_file = await message.bot.get_file(photo.file_id)

    fd, raw_path = tempfile.mkstemp(prefix="portrait_", suffix=".jpg")
    os.close(fd)
    path = Path(raw_path)
    await message.bot.download_file(telegram_file.file_path, destination=path)

    data = await state.get_data()
    language = str(data.get("language") or "ru")
    old_path = data.get("source_path")
    if old_path:
        Path(str(old_path)).unlink(missing_ok=True)

    await state.update_data(source_path=str(path))
    await state.set_state(PortraitFlow.waiting_style)
    await message.answer(
        "Выберите стиль:" if language == "ru" else "Choose a style:",
        reply_markup=style_keyboard(language),
    )


@router.message(PortraitFlow.waiting_photo)
async def photo_required(message: Message) -> None:
    await message.answer("Отправьте фотографию / Please send a photo")


@router.callback_query(PortraitFlow.waiting_style, F.data.startswith("style:"))
async def generate_portrait(callback: CallbackQuery, state: FSMContext) -> None:
    code = callback.data.split(":", 1)[1]
    style = STYLES.get(code)
    if style is None:
        await callback.answer("Unknown style", show_alert=True)
        return

    data = await state.get_data()
    language = str(data.get("language") or "ru")
    source_path = Path(str(data.get("source_path") or ""))
    if not source_path.exists():
        await callback.answer("Photo is missing", show_alert=True)
        await state.set_state(PortraitFlow.waiting_photo)
        return

    async with SessionFactory() as session:
        account = await get_or_create_account(session, telegram_id=callback.from_user.id)
        if account.credits <= 0:
            await callback.answer("No credits. Use /buy", show_alert=True)
            return

    await callback.answer()
    await callback.message.answer(
        "Генерирую изображение…" if language == "ru" else "Generating image…"
    )

    try:
        content = await build_generator(get_settings()).generate(
            source_path=source_path,
            style=style,
        )
    except Exception:
        await callback.message.answer(
            "Не удалось выполнить генерацию. Попробуйте позже."
            if language == "ru"
            else "Generation failed. Please try again later."
        )
        return

    async with SessionFactory() as session:
        account = await session.scalar(
            select(UserAccount).where(UserAccount.telegram_id == callback.from_user.id)
        )
        if account is None or account.credits <= 0:
            await callback.message.answer("Credit state changed. Run /balance.")
            return
        account.credits -= 1
        account.generations_used += 1
        await session.commit()
        remaining = account.credits

    await callback.message.answer_photo(
        BufferedInputFile(content, filename=f"{code}.jpg"),
        caption=(
            f"Готово. Осталось генераций: {remaining}"
            if language == "ru"
            else f"Done. Credits left: {remaining}"
        ),
    )
    source_path.unlink(missing_ok=True)
    await state.update_data(source_path=None)
    await state.set_state(PortraitFlow.waiting_photo)
