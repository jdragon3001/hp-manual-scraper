# Project Structure

## Directory Organization

```
hp-manual-scraper/
├── src/                          # Source code
│   ├── scraper.py               # Main scraper logic
│   ├── pdf_extractor.py         # PDF URL extraction
│   ├── downloader.py            # PDF download manager
│   └── utils.py                 # Utility functions
├── downloads/                    # Downloaded PDFs
│   ├── laptops/                 # Laptop manuals
│   │   ├── HP/                  # HP laptop manuals
│   │   ├── Dell/                # Dell laptop manuals
│   │   ├── Acer/                # Acer laptop manuals
│   │   └── ...                  # Other brands
│   └── desktops/                # Desktop manuals
│       ├── HP/                  # HP desktop manuals
│       ├── Dell/                # Dell desktop manuals
│       └── ...                  # Other brands
├── nextsteps/                   # Task planning
├── logs/                        # Log files
├── config.py                    # Configuration
├── requirements.txt             # Python dependencies
├── progress.json               # Download progress tracker
├── cmds.md                     # Command reference
├── DEPRECATED.txt              # Deprecated patterns
├── PROBLEM_LOG.txt             # Issues encountered
├── README.md                   # Project documentation
└── STRUCTURE.md                # This file
```

## File Descriptions

### Core Files
- **scraper.py**: Main entry point, orchestrates the scraping process
- **pdf_extractor.py**: Extracts manual metadata (brand, model, pages)
- **text_extractor.py**: Extracts complete text from all pages of manuals
- **downloader.py**: Legacy PDF downloader (not used due to manua.ls limitations)
- **pdf_downloader_playwright.py**: Playwright-based downloader (not used - generates corrupted PDFs)
- **utils.py**: Helper functions (logging, file handling, progress tracking)
- **config.py**: Centralized configuration

### Data Files
- **progress.json**: Tracks completed downloads to enable resume
- **logs/**: Contains timestamped log files

## Design Decisions

### Modular Architecture
Each component has a single responsibility:
- Scraper: Navigation and pagination
- Extractor: PDF URL extraction
- Downloader: File download and storage

### Progress Tracking
Uses JSON file to track state, allowing:
- Resume after interruption
- Skip already downloaded files
- Generate download statistics

### Error Handling
- Retry logic for network failures
- Graceful degradation on individual failures
- Comprehensive logging

### File Organization
- **Brand Folders**: Text files are organized into brand-specific subfolders
- **File Naming**: Format: `{Brand}_{Model}_{Pages}pages.txt`
- Example: `downloads/laptops/HP/HP_ENVY-x360_126pages.txt`

This organization makes it easy to:
- Browse manuals by brand
- Manage large collections
- Quickly locate specific manufacturer's products
- Search across all manuals using grep/text search tools

## Technology Stack
- **requests**: HTTP requests
- **BeautifulSoup4**: HTML parsing
- **Playwright**: JavaScript-heavy pages (if needed)
- **concurrent.futures**: Parallel downloads

