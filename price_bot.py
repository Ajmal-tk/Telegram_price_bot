import os
import asyncio
import threading
import http.server
import socketserver
import random
from dotenv import load_dotenv
from telegram import Update, BotCommand, ReplyKeyboardMarkup, MenuButtonCommands
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def start_http_server():
    port = int(os.getenv("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Health-check server running on port {port}")
        httpd.serve_forever()

class PriceBot:
    def __init__(self):
        load_dotenv()
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not self.token:
            raise ValueError("Missing TELEGRAM_BOT_TOKEN in environment.")
        self.application = Application.builder().token(self.token).build()

        self.setup_commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "How to use the bot"),
        ]

        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.search_product))
        self.application.post_init = self.post_init

    async def post_init(self, app):
        try:
            await app.bot.set_my_commands(self.setup_commands)
            await app.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
        except Exception as e:
            print(f"Warning: could not set commands: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = ReplyKeyboardMarkup([["/help"]], resize_keyboard=True)
        await update.message.reply_text(
            "Hi! Send me a product name to compare prices on Flipkart and Amazon.",
            reply_markup=keyboard,
        )

    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Usage:\nSend a product name (example: iPhone 13)\n"
            "I’ll fetch prices from Flipkart and Amazon."
        )

    async def search_product(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        flipkart = await self.get_flipkart_price(query)
        amazon = await self.get_amazon_price(query)

        msg = f"🔍 Price comparison for *{query}*:\n\n"
        msg += f"🛒 Flipkart: {flipkart or '❌ Not available'}\n"
        msg += f"📦 Amazon: {amazon or '❌ Not available'}\n"

        await update.message.reply_text(msg, parse_mode="Markdown")

    async def get_flipkart_price(self, query: str):
        url = f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context(user_agent=get_random_user_agent())
                page = await context.new_page()
                await page.goto(url, timeout=60000)
                content = await page.content()
                await browser.close()

            soup = BeautifulSoup(content, "html.parser")
            title = soup.select_one("div._4rR01T") or soup.select_one("a.IRpwTa") or soup.select_one("a.s1Q9rs")
            price = soup.select_one("div._30jeq3")
            if title and price:
                return f"{title.get_text(strip=True)} - {price.get_text(strip=True)}"
        except Exception as e:
            print("Flipkart error:", e)
        return None

    async def get_amazon_price(self, query: str):
        url = f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                context = await browser.new_context(user_agent=get_random_user_agent())
                page = await context.new_page()
                await page.goto(url, timeout=60000)
                content = await page.content()
                await browser.close()

            soup = BeautifulSoup(content, "html.parser")
            product = soup.select_one("div.s-main-slot div[data-component-type='s-search-result']")
            if not product:
                return None
            title = product.select_one("h2 span")
            price = product.select_one("span.a-price-whole")
            if title and price:
                return f"{title.get_text(strip=True)} - ₹{price.get_text(strip=True)}"
        except Exception as e:
            print("Amazon error:", e)
        return None

    def run(self):
        self.application.run_polling()

if __name__ == "__main__":
    threading.Thread(target=start_http_server, daemon=True).start()
    PriceBot().run()