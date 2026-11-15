

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

    from urllib.parse import quote_plus

    url = "https://www.google.com/search?q=" + quote_plus(query)

    await update.message.reply_text(
        "🔍 Поиск публичной информации:\n\n"
        f"Запрос: {query}\n\n"
        f"Результаты: {url}"
    )


async def handle_webhook(request):
    data = await request.json()
    update = Update.de_json(data, bot.bot)
    await bot.process_update(update)
    return web.Response(text="OK")


async def health(request):
    return web.Response(text="Bot is running!")


async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    await bot.initialize()

    await bot.initialize()
    await bot.start()

    server = web.Application()
    server.router.add_get("/", health)
    server.router.add_post("/webhook", handle_webhook)

    runner = web.AppRunner(server)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if render_url:
        await bot.bot.set_webhook(render_url.rstrip("/") + "/webhook")

    logging.info("Бот запущен!")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
