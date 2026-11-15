
import os
import logging
import requests

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔎 OSINT BOT\n\n"
        "Я ищу публичную информацию в интернете.\n\n"
        "Отправь имя или username для поиска."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if len(query) < 2 or len(query) > 100:
        await update.message.reply_text("Введите запрос от 2 до 100 символов.")
        return

    await update.message.reply_text("🔍 Ищу публичные упоминания...")

    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()

        results = []

        abstract = data.get("AbstractText")
        if abstract:
            results.append(abstract)

        for item in data.get("RelatedTopics", []):
            if isinstance(item, dict) and item.get("Text"):
                results.append(item["Text"])

        if not results:
            await update.message.reply_text(
                "Ничего не найдено. Попробуй другой запрос."
            )
            return

        message = "📄 Публичные результаты:\n\n"
        for item in results[:5]:
            message += "• " + item[:500] + "\n\n"

        await update.message.reply_text(message[:4000])

    except requests.RequestException:
        await update.message.reply_text("Ошибка соединения с поиском.")

async def main():
    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))

    print("OSINT BOT запущен")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    import asyncio
    import asyncio
    asyncio.run(main())
