
import os
import asyncio
import logging
import re

from urllib.parse import quote_plus, urlparse, parse_qs

import aiohttp
from aiohttp import web
from bs4 import BeautifulSoup

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = None


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🌐 Веб-поиск",
                callback_data="web"
            ),
            InlineKeyboardButton(
                "📱 Проверка номера",
                callback_data="phone"
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Соцсети",
                callback_data="social"
            ),
            InlineKeyboardButton(
                "🌍 Домен и IP",
                callback_data="domain"
            )
        ],
        [
            InlineKeyboardButton(
                "🏢 Компании",
                callback_data="company"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "web"

    await update.message.reply_text(
        "🔎 BURMALDA OSINT BOT\n\n"
        "Выбери категорию поиска:",
        reply_markup=main_menu()
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["mode"] = "web"

    await update.message.reply_text(
        "Выбери категорию:",
        reply_markup=main_menu()
    )


async def category_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    mode = query.data
    context.user_data["mode"] = mode

    messages = {
        "web": "🌐 Отправь запрос для поиска в интернете.",
        "phone": (
            "📱 Отправь номер телефона.\n"
            "Я проверю только его формат и страну."
        ),
        "social": (
            "💬 Отправь ссылку на публичную страницу "
            "соцсети или организации."
        ),
        "domain": "🌍 Отправь домен или IP-адрес.",
        "company": (
            "🏢 Отправь название компании или её ИНН."
        )
    }

    await query.edit_message_text(
        messages.get(mode, "Выбери категорию:"),
        reply_markup=main_menu()
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()
    mode = context.user_data.get("mode", "web")

    if len(query) < 2 or len(query) > 100:
        await update.message.reply_text(
            "Запрос должен содержать от 2 до 100 символов."
        )
        return

    if mode == "phone":
        digits = re.sub(r"\D", "", query)

        if not 7 <= len(digits) <= 15:
            await update.message.reply_text(
                "Проверь номер: нужно от 7 до 15 цифр."
            )
            return

        await update.message.reply_text(
            "✅ Формат номера подходит.\n"
            "Поиск владельца и частных данных не поддерживается."
        )
        return

    await update.message.reply_text(
        "🔎 Ищу публичную информацию..."
    )

    search_url = (
        "https://html.duckduckgo.com/html/?q="
        + quote_plus(query)
    )

    try:
        timeout = aiohttp.ClientTimeout(total=20)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                search_url,
                headers={"User-Agent": "Mozilla/5.0"}
            ) as response:

                if response.status != 200:
                    raise RuntimeError(
                        "Ошибка поисковика: "
                        + str(response.status)
                    )

                html = await response.text()

        soup = BeautifulSoup(html, "html.parser")
        results = soup.select(".result")

        if not results:
            await update.message.reply_text(
                "Результатов нет. Попробуй другой запрос."
            )
            return

        message = "🔎 Результаты поиска:\n\n"
        count = 0

        for result in results:
            title_tag = result.select_one(".result__a")
            snippet_tag = result.select_one(".result__snippet")

            if not title_tag:
                continue

            title = title_tag.get_text(" ", strip=True)
            link = title_tag.get("href", "")

            snippet = (
                snippet_tag.get_text(" ", strip=True)
                if snippet_tag
                else "Описание отсутствует."
            )

            parsed = urlparse(link)
            params = parse_qs(parsed.query)

            if "uddg" in params:
                link = params["uddg"][0]
            elif link.startswith("//"):
                link = "https:" + link

            if not link.startswith(("https://", "http://")):
                continue

            count += 1

            message += (
                f"{count}. {title}\n"
                f"{snippet[:200]}\n"
                f"{link}\n\n"
            )

            if count >= 5:
                break

        if count == 0:
            await update.message.reply_text(
                "Не удалось получить ссылки из результатов."
            )
            return

        await update.message.reply_text(
            message[:4000],
            disable_web_page_preview=True
        )

    except Exception:
        logger.exception("Ошибка поиска")

        await update.message.reply_text(
            "Ошибка поиска. Попробуй позже."
        )


async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot.bot)

        await bot.process_update(update)

        return web.Response(text="OK")

    except Exception:
        logger.exception("Ошибка webhook")

        return web.Response(
            text="Webhook error",
            status=500
        )


async def health(request):
    return web.Response(text="Bot is running!")


async def main():
    global bot

    if not TOKEN:
        raise RuntimeError("Не задан BOT_TOKEN")

    bot = Application.builder().token(TOKEN).build()

    bot.add_handler(CommandHandler("start", start))
    bot.add_handler(CommandHandler("menu", menu))

    bot.add_handler(
        CallbackQueryHandler(category_callback)
    )

    bot.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            search
        )
    )

    await bot.initialize()
    await bot.start()

    server = web.Application()

    server.router.add_get("/", health)
    server.router.add_post("/webhook", handle_webhook)

    runner = web.AppRunner(server)
    await runner.setup()

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        PORT
    )

    await site.start()

    render_url = os.getenv("RENDER_EXTERNAL_URL")

    if not render_url:
        raise RuntimeError("Не задан RENDER_EXTERNAL_URL")

    webhook_url = render_url.rstrip("/") + "/webhook"

    await bot.bot.set_webhook(webhook_url)

    logger.info("Бот запущен и меню настроено!")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())


