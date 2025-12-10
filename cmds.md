# Command Reference

## Environment Setup

### Quick Setup (All-in-One)
```bash
# Create environment with Python 3.11
conda create -n manual-scraper python=3.11 -y

# Activate environment
conda activate manual-scraper

# Install all Python dependencies
pip install -r requirements.txt

# Install Playwright Chromium browser
python -m playwright install chromium
```

### Individual Steps

#### Create Conda Environment
```bash
conda create -n manual-scraper python=3.11 -y
```

#### Activate Environment
```bash
conda activate manual-scraper
```

#### Install Dependencies
```bash
pip install -r requirements.txt
```

#### Install Playwright Browser
```bash
python -m playwright install chromium
```

#### Verify Installation
```bash
python -c "import playwright, requests, bs4, aiohttp, tqdm; print('All dependencies working!')"
```

## Running the Scraper

### Start Full Scrape (Laptops + Desktops)
```bash
conda activate manual-scraper
python scraper.py
```

### Scrape Only Laptops (15,193+ manuals, ~7-8 hours)
```bash
conda activate manual-scraper
python scraper.py --type laptops
```

### Scrape Only Desktops (5,111+ manuals, ~3-4 hours)
```bash
conda activate manual-scraper
python scraper.py --type desktops
```

### Scrape Single Brand
```bash
conda activate manual-scraper
python scrape_brand.py HP
```

### Scrape Single Brand (Parallel-Safe Mode)
Use this version when running multiple terminals in parallel:
```bash
conda activate manual-scraper
python scrape_brand_parallel_safe.py HP
```

**Recommended: Run only 2 instances in parallel** (not 3+) to avoid rate limiting.

### Scrape Multiple Small Brands (Sequential)
```bash
# Using Python script (Recommended - prevents overlap)
conda activate manual-scraper
python scrape_small_brands_sequential.py
```

Or using batch file (Windows):
```bash
conda activate manual-scraper
run_small_brands.bat
```

### Scrape Multiple Brands (PowerShell one-liner)
```powershell
conda activate manual-scraper; python scrape_brand.py NCS; python scrape_brand.py PRODVX; python scrape_brand.py KRAMER; python scrape_brand.py TRIPP-LITE; python scrape_brand.py VTECH; python scrape_brand.py MOXA; python scrape_brand.py AAEON; python scrape_brand.py PHILIPS; python scrape_brand.py INFOCUS; python scrape_brand.py ADVANCE; python scrape_brand.py BEMATECH; python scrape_brand.py OPTOMA; python scrape_brand.py CORSAIR; python scrape_brand.py AXIS; python scrape_brand.py NCOMPUTING; python scrape_brand.py CYBERNET; python scrape_brand.py ARCTIC-COOLING; python scrape_brand.py DELL-WYSE; python scrape_brand.py SEAGATE; python scrape_brand.py PYLE; python scrape_brand.py PRIXTON; python scrape_brand.py CTL; python scrape_brand.py GENERAL-DYNAMICS-ITRONIX; python scrape_brand.py DYNABOOK; python scrape_brand.py EVGA; python scrape_brand.py CRAIG; python scrape_brand.py VISUAL-LAND; python scrape_brand.py EMATIC; python scrape_brand.py ARCHOS; python scrape_brand.py HERCULES; python scrape_brand.py CORE-INNOVATIONS; python scrape_brand.py KIANO; python scrape_brand.py COBY; python scrape_brand.py BELINEA; python scrape_brand.py ODYS; python scrape_brand.py HYUNDAI; python scrape_brand.py ZEBRA; python scrape_brand.py VULCAN; python scrape_brand.py TCL; python scrape_brand.py XPLORE; python scrape_brand.py RAZOR; python scrape_brand.py NEXOC; python scrape_brand.py HTC; python scrape_brand.py SCHNEIDER; python scrape_brand.py FLYBOOK; python scrape_brand.py HUMANSCALE; python scrape_brand.py BENQ; python scrape_brand.py ROLAND; python scrape_brand.py WOOOD; python scrape_brand.py ATARI; python scrape_brand.py FOXCONN; python scrape_brand.py FAYTECH; python scrape_brand.py GIADA; python scrape_brand.py PROMETHEAN; python scrape_brand.py TREKSTOR; python scrape_brand.py MICROTECH; python scrape_brand.py LOCKNCHARGE; python scrape_brand.py XPG; python scrape_brand.py MPMAN; python scrape_brand.py VXL; python scrape_brand.py WYSE; python scrape_brand.py VIEWSONIC; python scrape_brand.py JYSK; python scrape_brand.py TARGA; python scrape_brand.py DURABOOK; python scrape_brand.py BEKO; python scrape_brand.py AIRIS; python scrape_brand.py XIAOMI; python scrape_brand.py HAIER; python scrape_brand.py MAXDATA; python scrape_brand.py ELO; python scrape_brand.py IGEL; python scrape_brand.py NEC; python scrape_brand.py KOGAN; python scrape_brand.py SHUTTLE; python scrape_brand.py SYSTEM76; python scrape_brand.py TECHBITE; python scrape_brand.py VIZIO; python scrape_brand.py THOMSON; python scrape_brand.py FUJITSU-SIEMENS; python scrape_brand.py MICROSOFT; python scrape_brand.py AORUS; python scrape_brand.py COMPAQ; python scrape_brand.py RAZER; python scrape_brand.py IBM; python scrape_brand.py INTEL; python scrape_brand.py ADVANTECH; python scrape_brand.py HUAWEI; python scrape_brand.py HONOR; python scrape_brand.py ECS; python scrape_brand.py ASROCK; python scrape_brand.py APPLE; python scrape_brand.py LG; python scrape_brand.py GETAC; python scrape_brand.py ZOTAC; python scrape_brand.py PACKARD-BELL; python scrape_brand.py PANASONIC
```

### Resume Interrupted Download (automatic)
The scraper automatically resumes from where it left off using `progress.json`

### Verbose Logging
```bash
python scraper.py --verbose
```

## Expected Runtime
- Single manual: ~84 seconds (for 126 pages)
- Laptops: 15,193 manuals × ~60 sec avg = ~10-12 hours
- Desktops: 5,111 manuals × ~60 sec avg = ~3-4 hours  
- **Total: ~13-16 hours** for complete scrape

## Maintenance

### Check Progress
```bash
python -c "import json; print(json.load(open('progress.json')))"
```

### Clear Progress (restart from scratch)
```bash
del progress.json  # Windows
rm progress.json   # Linux/Mac
```

### View Logs
```bash
cat logs/scraper_latest.log
```

## Testing

### Test PDF Extraction on Single Page
```bash
python -c "from src.pdf_extractor import extract_pdf_url; print(extract_pdf_url('https://www.manua.ls/hp/envy-x360/manual'))"
```

## Manual Type Detection (Added Dec 2025)

Some manuals on manua.ls use image rendering instead of HTML text.
These require OCR to extract content.

### Detect Manual Rendering Type
```bash
python detect_manual_type.py
```
This will show if a manual uses:
- `html_text` - Works with existing scraper
- `image` - Requires OCR (Tesseract)

### Deep HTML Investigation  
```bash
python investigate_page_html.py
```
Analyzes page structure, font encoding, and text elements.

### Font Decoder Analysis
```bash
python font_decoder.py
```
Attempts to decode custom font mappings (limited success).

## OCR Extraction (For Image-Based Manuals)

### Prerequisites - Install Tesseract OCR
1. Download from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer
3. Verify: `tesseract --version`

### Run OCR Extractor
```bash
python ocr_extractor.py
```
Downloads page images and extracts text via OCR.

### Comprehensive Evaluation
```bash
python comprehensive_evaluation.py
```
Tests multiple extraction methods on a single manual.

