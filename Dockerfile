FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates curl unzip fonts-liberation \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libx11-xcb1 libnss3-dev libxss1 xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

# Install Playwright and its browsers
RUN pip install playwright
RUN playwright install chromium

COPY . .

CMD ["python", "price_bot.py"]
