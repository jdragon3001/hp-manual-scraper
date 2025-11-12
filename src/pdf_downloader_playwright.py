"""
PDF downloader using Playwright to print HTML pages as PDF
Since manua.ls uses pdf2htmlEX and doesn't provide direct PDF downloads
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path
import time
from src.utils import setup_logging, sanitize_filename
import config

logger = setup_logging(__name__)

def download_manual_as_pdf(manual_url: str, output_path: Path, manual_info: dict = None) -> bool:
    """
    Download a manual by printing the HTML page as PDF using Playwright
    
    Args:
        manual_url: URL of the manual page
        output_path: Path to save the PDF
        manual_info: Optional manual information
    
    Returns:
        True if successful, False otherwise
    """
    if output_path.exists():
        logger.info(f"File already exists: {output_path.name}")
        return True
    
    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with sync_playwright() as p:
            logger.info(f"Launching browser for: {output_path.name}")
            
            # Launch browser (headless mode)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to manual page
            logger.info(f"Loading page: {manual_url}")
            page.goto(manual_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for the PDF viewer to load
            logger.info("Waiting for viewer to load...")
            page.wait_for_selector('.viewer-page', timeout=20000)
            
            # Give it a moment to fully render
            logger.info("Allowing page to render...")
            time.sleep(3)
            
            # Print to PDF
            logger.info(f"Printing to PDF: {output_path.name}")
            page.pdf(
                path=str(output_path),
                format='A4',
                print_background=True,
                margin={
                    'top': '0.5in',
                    'right': '0.5in',
                    'bottom': '0.5in',
                    'left': '0.5in'
                }
            )
            
            browser.close()
            
            logger.info(f"Successfully saved: {output_path.name}")
            return True
            
    except PlaywrightTimeout as e:
        logger.error(f"Timeout loading {manual_url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Error downloading {manual_url}: {e}")
        # Clean up partial file
        if output_path.exists():
            output_path.unlink()
        return False

def download_manual_playwright(manual_info: dict, category: str) -> bool:
    """
    Download a manual using Playwright with proper naming and location
    
    Args:
        manual_info: Dictionary with manual information including url
        category: 'laptops' or 'desktops'
    
    Returns:
        True if successful, False otherwise
    """
    if not manual_info or not manual_info.get('url'):
        logger.warning(f"No URL for manual")
        return False
    
    # Determine base output directory
    base_dir = config.LAPTOP_DIR if category == 'laptops' else config.DESKTOP_DIR
    
    # Create brand subfolder
    brand = manual_info.get('brand', 'Unknown')
    brand_folder = sanitize_filename(brand)
    output_dir = base_dir / brand_folder
    
    # Ensure brand directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    model = manual_info.get('model', 'Unknown')
    pages = manual_info.get('pages', '')
    
    if pages:
        filename = f"{brand}_{model}_{pages}pages.pdf"
    else:
        filename = f"{brand}_{model}.pdf"
    
    filename = sanitize_filename(filename)
    output_path = output_dir / filename
    
    # Download using Playwright
    success = download_manual_as_pdf(manual_info['url'], output_path, manual_info)
    
    # Polite delay
    if success:
        time.sleep(config.REQUEST_DELAY)
    
    return success

