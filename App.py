
import os
import logging
import asyncio
from aiohttp import web
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

logging.basicConfig(level=logging.INFO)

telegram_app = Application.builder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 OSINT BOT\n\n"
        "Я ищу общедоступные сведения и публичные упоминания.\n"
        "Отправь поисковый запрос."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if len(query) < 2 or len(query) > 100:
        await update.message.reply_text("Запрос должен содержать от 2 до 100 символов.")
        return

    await update.message.reply_text(
        "🔍 Поиск публичных упоминаний:\n\n"
        f"Запрос: {query}\n\n"
        "Открыть поиск:\n"
        f"https://www.google.com/search?q={query.replace(' ', '+')}"
    )

async def webhook(request):
    data = await request.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return web.Response(text="OK")

async def health(request):
    return web.Response(text="Bot is running")

async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN не задан")

    await telegram_app.initialize()
    await telegram_app.start()

    server = web.Application()
    server.router.add_post("/webhook", webhook)
    server.router.add_get("/", health)

    runner = web.AppRunner(server)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    webhook_url = os.getenv("RENDER_EXTERNAL_URL")
    if webhook_url:
        await telegram_app.bot.set_webhook(webhook_url + "/webhook")

    logging.info("OSINT BOT запущен")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

