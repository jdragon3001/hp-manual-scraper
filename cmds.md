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

