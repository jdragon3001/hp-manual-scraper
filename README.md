# HP Manual Scraper

## Overview
This project scrapes and downloads PDF manuals from manua.ls for laptops and desktops.

## Features
- Scrapes laptop manuals from: https://www.manua.ls/computers-and-accessories/laptops (15,193+ manuals)
- Scrapes desktop manuals from: https://www.manua.ls/computers-and-accessories/desktops (5,111+ manuals)
- Extracts complete manual text from ALL pages
- Handles pagination automatically (126+ pages per manual)
- Saves as formatted text files organized by brand
- Progress tracking and resume capability
- Error handling and retry logic

## Why Text Files Instead of PDFs?
manua.ls uses pdf2htmlEX technology that converts PDFs to HTML for web viewing. They don't provide direct PDF downloads. Text extraction:
- ✅ Gets ALL pages of content (not just the first page)
- ✅ Preserves formatting (TOC, specs, FAQs)
- ✅ Much faster than browser automation
- ✅ Searchable and easy to process
- ✅ ~84 seconds per 126-page manual

## Setup

### 1. Create Conda Environment
```bash
conda create -n manual-scraper python=3.11
conda activate manual-scraper
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Playwright browsers (if using Playwright)
```bash
playwright install chromium
```

## Usage

### Run the scraper
```bash
python scraper.py
```

### Configuration
Edit `config.py` to modify:
- Target URLs (laptops/desktops)
- Download directory
- Concurrent downloads
- Retry attempts

## Project Structure
See `STRUCTURE.md` for detailed file organization.

## Output
Extracted manuals will be organized by brand as text files:
- `downloads/laptops/{Brand}/` - All laptop manuals for each brand
- `downloads/desktops/{Brand}/` - All desktop manuals for each brand

Example:
- `downloads/laptops/HP/HP_ENVY-x360_126pages.txt`
- `downloads/laptops/Dell/Dell_Inspiron-15_148pages.txt`
- `downloads/desktops/HP/HP_Pavilion-Desktop_95pages.txt`

Each text file contains:
- Product title and information
- Complete table of contents
- ALL pages of manual content (extracted from each page)
- Full specifications
- Frequently asked questions

## Progress Tracking
The scraper creates a `progress.json` file to track downloaded manuals and allow resuming interrupted downloads.

## Created: November 12, 2025

