"""
Configuration for the manual scraper
"""
import os
from pathlib import Path

# Base URLs
LAPTOP_URL = "https://www.manua.ls/computers-and-accessories/laptops"
DESKTOP_URL = "https://www.manua.ls/computers-and-accessories/desktops"

# Download settings
DOWNLOAD_DIR = Path("downloads")
LAPTOP_DIR = DOWNLOAD_DIR / "laptops"
DESKTOP_DIR = DOWNLOAD_DIR / "desktops"
LOG_DIR = Path("logs")

# Ensure directories exist
DOWNLOAD_DIR.mkdir(exist_ok=True)
LAPTOP_DIR.mkdir(exist_ok=True)
DESKTOP_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Scraping settings
MAX_RETRIES = 3
TIMEOUT = 30  # seconds
CONCURRENT_DOWNLOADS = 5
REQUEST_DELAY = 1  # seconds between requests to be polite

# Progress tracking
PROGRESS_FILE = "progress.json"

# Headers for requests
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

# Logging
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = 'INFO'

