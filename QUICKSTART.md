# Quick Start Guide

## Get Started in 3 Steps

### 1. Activate Environment
```bash
conda activate manual-scraper
```

### 2. Run the Scraper
```bash
python scraper.py
```

That's it! The scraper will:
- Extract 15,193+ laptop manuals
- Extract 5,111+ desktop manuals  
- Organize by brand folders
- Save complete formatted text files
- Auto-resume if interrupted
- Track progress in `progress.json`

### 3. Find Your Manuals
```
downloads/
├── laptops/
│   ├── HP/
│   │   ├── HP_ENVY-x360_126pages.txt
│   │   ├── HP_Pavilion-15_166pages.txt
│   │   └── ...
│   ├── Dell/
│   ├── Acer/
│   └── ...
└── desktops/
    ├── HP/
    ├── Dell/
    └── ...
```

## What Gets Extracted?

Each `.txt` file contains:
- ✅ Title & product info
- ✅ Table of contents
- ✅ **ALL pages** of manual content (100+ pages)
- ✅ Complete specifications
- ✅ FAQs

## Estimated Time
- **Total Runtime**: 13-16 hours for all manuals
- **Per Manual**: ~60-84 seconds (depending on pages)
- Can run overnight or in background

## Monitor Progress
Watch the console for real-time progress:
```
Downloading laptops: 45%|████████      | 6870/15193 [3:42:15<4:15:30, 0.54it/s]
```

Logs are saved to `logs/` directory.

Created: November 12, 2025

