"""
PDF download manager
"""
import requests
from pathlib import Path
from typing import Optional
import time
import config
from src.utils import setup_logging, sanitize_filename, retry_on_failure

logger = setup_logging(__name__)

def download_pdf(pdf_url: str, output_path: Path, manual_info: dict = None) -> bool:
    """
    Download a PDF file
    
    Args:
        pdf_url: URL of the PDF
        output_path: Path to save the PDF
        manual_info: Optional manual information for better error messages
    
    Returns:
        True if successful, False otherwise
    """
    if output_path.exists():
        logger.info(f"File already exists: {output_path.name}")
        return True
    
    def _download():
        logger.info(f"Downloading: {output_path.name}")
        response = requests.get(pdf_url, headers=config.HEADERS, timeout=config.TIMEOUT, stream=True)
        response.raise_for_status()
        
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Download in chunks
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Successfully downloaded: {output_path.name}")
        return True
    
    try:
        result = retry_on_failure(_download)
        return result is not None
    except Exception as e:
        logger.error(f"Failed to download {pdf_url}: {e}")
        # Clean up partial download
        if output_path.exists():
            output_path.unlink()
        return False

def generate_filename(manual_info: dict, category: str) -> str:
    """
    Generate a filename from manual information
    
    Args:
        manual_info: Dictionary with brand, model, pages
        category: 'laptops' or 'desktops'
    
    Returns:
        Sanitized filename
    """
    brand = manual_info.get('brand', 'Unknown')
    model = manual_info.get('model', 'Unknown')
    pages = manual_info.get('pages', '')
    
    # Create filename: Brand_Model_Npages.pdf
    if pages:
        filename = f"{brand}_{model}_{pages}pages.pdf"
    else:
        filename = f"{brand}_{model}.pdf"
    
    return sanitize_filename(filename)

def download_manual(manual_info: dict, category: str) -> bool:
    """
    Download a manual with proper naming and location
    
    Args:
        manual_info: Dictionary with manual information including pdf_url
        category: 'laptops' or 'desktops'
    
    Returns:
        True if successful, False otherwise
    """
    if not manual_info or not manual_info.get('pdf_url'):
        logger.warning(f"No PDF URL for manual: {manual_info.get('url', 'Unknown')}")
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
    filename = generate_filename(manual_info, category)
    output_path = output_dir / filename
    
    # Download
    success = download_pdf(manual_info['pdf_url'], output_path, manual_info)
    
    # Polite delay between downloads
    if success:
        time.sleep(config.REQUEST_DELAY)
    
    return success

