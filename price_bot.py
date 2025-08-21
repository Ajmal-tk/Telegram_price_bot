import re
import random
import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.error import InvalidToken

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN or BOT_TOKEN == "YOUR_TOKEN_HERE":
    raise InvalidToken("❌ BOT_TOKEN is missing. Please set it as an environment variable in Render.")

# -----------------------------
# Flipkart Scraper
# -----------------------------
async def scrape_flipkart_price(url: str, max_retries: int = 3) -> str:
    selectors = [
        "._30jeq3",  # Flipkart price
        "._16Jk6d",  # Alternate
    ]

    for attempt in range(1, max_retries + 1):
        browser = None
        try:
            logging.info(f"[Flipkart] Attempt {attempt}")

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                )
                page = await context.new_page()

                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(800, 2000))

                for selector in selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=8000)
                        price_text = await element.inner_text()
                        price = re.sub(r"[^\d₹,.]", "", price_text)
                        if price:
                            logging.info(f"[Flipkart] Found price {price}")
                            await context.close()
                            await browser.close()
                            return price
                    except Exception as se:
                        logging.warning(f"[Flipkart] Selector {selector} failed: {se}")

                await context.close()
                await browser.close()

        except Exception as e:
            logging.error(f"[Flipkart] Exception {e}")
            if browser:
                try:
                    await browser.close()
                except:
                    pass

        await asyncio.sleep(attempt * 2)

    return "Not Found"


# -----------------------------
# Amazon Scraper
# -----------------------------
async def scrape_amazon_price(url: str, max_retries: int = 3) -> str:
    selectors = [
        "#priceblock_ourprice",
        "#priceblock_dealprice",
        "#priceblock_saleprice",
        "span.a-price span.a-offscreen",
    ]

    for attempt in range(1, max_retries + 1):
        browser = None
        try:
            logging.info(f"[Amazon] Attempt {attempt}")

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
                )
                page = await context.new_page()

                await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(800, 2000))

                for selector in selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=8000)
                        price_text = await element.inner_text()
                        price = re.sub(r"[^\d₹,.]", "", price_text)
                        if price:
                            logging.info(f"[Amazon] Found price {price}")
                            await context.close()
                            await browser.close()
                            return price
                    except Exception as se:
                        logging.warning(f"[Amazon] Selector {selector} failed: {se}")

                await context.close()
                await browser.close()

        except Exception as e:
            logging.error(f"[Amazon] Exception {e}")
            if browser:
                try:
                    await browser.close()
                except:
                    pass

        await asyncio.sleep(attempt * 2)

    return "Not Found"


# -----------------------------
# Telegram Bot Commands
# -----------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Use: /compare <flipkart_url> <amazon_url>")


async def compare(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /compare <flipkart_url> <amazon_url>")
        return

    flip_url, amz_url = context.args
    await update.message.reply_text("🔍 Fetching prices, please wait...")

    flip_task = asyncio.create_task(scrape_flipkart_price(flip_url))
    amz_task = asyncio.create_task(scrape_amazon_price(amz_url))

    flip_price, amz_price = await asyncio.gather(flip_task, amz_task)

    reply = f"🛒 Flipkart: {flip_price}\n📦 Amazon: {amz_price}"
    await update.message.reply_text(reply)


def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("compare", compare))
    app.run_polling()


# -----------------------------
# Dummy HTTP server for Render health check
# -----------------------------
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def start_health_server():
    port = int(os.environ.get("PORT", 8080))  # Render requires binding to $PORT
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logging.info(f"Dummy HTTP server running on port {port}")
    server.serve_forever()


# -----------------------------
# Main Entry
# -----------------------------
if __name__ == "__main__":
    # Start dummy webserver in background thread
    threading.Thread(target=start_health_server, daemon=True).start()

    # Run the actual bot (polls Telegram)
    run_bot()
