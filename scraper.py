"""
Main entry point for the manua.ls manual scraper
"""
import argparse
from src.scraper import ManualscrScraper
from src.utils import setup_logging

logger = setup_logging(__name__)

def main():
    """Main entry point with command-line argument parsing"""
    parser = argparse.ArgumentParser(description='Scrape manuals from manua.ls')
    parser.add_argument(
        '--type',
        choices=['laptops', 'desktops', 'both'],
        default='both',
        help='Type of manuals to scrape (default: both)'
    )
    parser.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous progress (automatically done by default)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Dry run - list manuals without downloading'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging'
    )
    
    args = parser.parse_args()
    
    # Determine categories to scrape
    if args.type == 'both':
        categories = ['laptops', 'desktops']
    else:
        categories = [args.type]
    
    logger.info(f"Starting scraper for: {', '.join(categories)}")
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No downloads will be performed")
    
    # Create and run scraper
    scraper = ManualscrScraper()
    scraper.run(categories)

if __name__ == '__main__':
    main()

