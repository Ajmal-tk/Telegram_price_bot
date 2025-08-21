#!/usr/bin/env bash
# Exit if any command fails
set -o errexit

# Install Python dependencies
pip install -r requirements.txt

# Install Chromium for Playwright
playwright install --with-deps chromium

bash
chmod +x build.sh