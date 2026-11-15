

import os
import asyncio
import logging
from aiohttp import web
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(level=logging.INFO)

bot = Application.builder().token(TOKEN).build()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 Добро пожаловать в Public OSINT Bot!\n\n"
        "Я помогаю искать публичные упоминания.\n"
        "Отправь поисковый запрос."
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if len(query) < 2 or len(query) > 100:
        await update.message.reply_text("Запрос должен быть от 2 до 100 символов.")
        return

    from urllib.par
