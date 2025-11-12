"""
Utility functions for the scraper
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, Set
from datetime import datetime
import config

def setup_logging(name: str) -> logging.Logger:
    """
    Setup logging configuration
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(config.LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler
    log_file = config.LOG_DIR / f"scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(config.LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    return logger

def load_progress() -> Dict[str, Set[str]]:
    """
    Load download progress from file
    
    Returns:
        Dictionary with 'laptops' and 'desktops' keys containing sets of downloaded URLs
    """
    if not Path(config.PROGRESS_FILE).exists():
        return {'laptops': set(), 'desktops': set()}
    
    try:
        with open(config.PROGRESS_FILE, 'r') as f:
            data = json.load(f)
            return {
                'laptops': set(data.get('laptops', [])),
                'desktops': set(data.get('desktops', []))
            }
    except Exception as e:
        logging.error(f"Error loading progress: {e}")
        return {'laptops': set(), 'desktops': set()}

def save_progress(progress: Dict[str, Set[str]]):
    """
    Save download progress to file
    
    Args:
        progress: Dictionary with 'laptops' and 'desktops' keys containing sets of downloaded URLs
    """
    try:
        data = {
            'laptops': list(progress['laptops']),
            'desktops': list(progress['desktops'])
        }
        with open(config.PROGRESS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving progress: {e}")

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    return filename

def retry_on_failure(func, max_retries: int = config.MAX_RETRIES, delay: int = 2):
    """
    Retry a function on failure
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
    
    Returns:
        Result of function or None on failure
    """
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt < max_retries - 1:
                logging.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                time.sleep(delay)
            else:
                logging.error(f"All {max_retries} attempts failed: {e}")
                return None

