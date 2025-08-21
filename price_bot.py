import re
import random
import asyncio
import logging
from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")

# -----------------------------
# Flipkart Scraper
# -----------------------------
async def scrape_flipkart_price(url: str, max_retries: int = 3) -> str:
    selectors = [
        "._30jeq3",  # Flipkart price
        "._16Jk6d",  # Alternate
    ]

    for attempt in range(1, max_retries + 1):
        try:
            print(f"[Flipkart] Attempt {attempt}...")

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

                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(500, 1500))

                for selector in selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=8000)
                        price_text = await element.inner_text()
                        price = re.sub(r"[^\d₹,.]", "", price_text)
                        if price:
                            await browser.close()
                            return price
                    except Exception:
                        continue

                await browser.close()
        except Exception as e:
            print(f"[Flipkart] Attempt {attempt} failed: {e}")

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
        try:
            print(f"[Amazon] Attempt {attempt}...")

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

                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(random.randint(500, 1500))

                for selector in selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=8000)
                        price_text = await element.inner_text()
                        price = re.sub(r"[^\d₹,.]", "", price_text)
                        if price:
                            await browser.close()
                            return price
                    except Exception:
                        continue

                await browser.close()
        except Exception as e:
            print(f"[Amazon] Attempt {attempt} failed: {e}")

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

    reply = f"🛒 Flipkart: {flip_price}\n\n📦 Amazon: {amz_price}"
    await update.message.reply_text(reply)


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("compare", compare))
    app.run_polling()


if __name__ == "__main__":
    main()
