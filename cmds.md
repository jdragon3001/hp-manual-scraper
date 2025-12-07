# Command Reference

## Environment Setup

### Create Conda Environment
```bash
conda create -n manual-scraper python=3.11
```

### Activate Environment
```bash
conda activate manual-scraper
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Install Playwright (if needed)
```bash
playwright install chromium
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

