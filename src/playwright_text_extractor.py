"""
Extract manual text using Playwright to handle JavaScript-rendered content
This is the proper solution since manua.ls loads content dynamically
"""
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from typing import Optional
import config
from src.utils import setup_logging, sanitize_filename
from pathlib import Path
import time
import re

logger = setup_logging(__name__)

def extract_page_text_playwright(page, page_num: int) -> str:
    """
    Extract text from a single rendered page using Playwright
    
    Args:
        page: Playwright page object
        page_num: Page number
    
    Returns:
        Text content of the page
    """
    try:
        # Wait for the content to load
        page.wait_for_selector('.viewer-page', timeout=15000)
        time.sleep(3)  # Critical: wait for JS rendering to complete
        
        # Get all text from the viewer page
        # Use innerText which gives us properly formatted text with spaces
        text_content = page.eval_on_selector('.viewer-page', '(element) => element.innerText')
        
        return text_content if text_content else ""
        
    except Exception as e:
        logger.error(f"Error extracting page {page_num} with Playwright: {e}")
        return ""

def extract_manual_text_playwright(manual_url: str) -> Optional[str]:
    """
    Extract complete manual text using Playwright
    
    Args:
        manual_url: URL of the manual page
    
    Returns:
        Complete formatted text content or None
    """
    try:
        with sync_playwright() as p:
            # Launch browser in headless mode
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=config.HEADERS['User-Agent']
            )
            page = context.new_page()
            
            logger.info(f"Loading manual page with Playwright...")
            page.goto(manual_url, wait_until='domcontentloaded', timeout=30000)
            
            # Wait for main content to load
            page.wait_for_selector('h1', timeout=10000)
            time.sleep(2)  # Give JavaScript time to render
            
            output = []
            
            # Get title
            try:
                title = page.inner_text('h1')
                output.append("=" * 80)
                output.append(title.upper())
                output.append("=" * 80)
                output.append("")
            except:
                pass
            
            # Get product info/subtitle
            try:
                subtitle = page.inner_text('.manual__subtitle')
                output.append(subtitle)
                output.append("-" * 80)
                output.append("")
            except:
                pass
            
            # Get description
            try:
                description = page.inner_text('.manual__description')
                output.append("DESCRIPTION:")
                output.append(description)
                output.append("")
                output.append("-" * 80)
                output.append("")
            except:
                pass
            
            # Get Table of Contents
            try:
                toc_items = page.query_selector_all('.toc__container a')
                if toc_items:
                    output.append("TABLE OF CONTENTS:")
                    output.append("")
                    for item in toc_items:
                        page_num = item.get_attribute('data-page') or ''
                        text = item.inner_text()
                        if text:
                            output.append(f"  Page {page_num:>3}: {text}")
                    output.append("")
                    output.append("-" * 80)
                    output.append("")
            except:
                pass
            
            # Get total number of pages
            try:
                # Look for page indicator like "1 / 126"
                page_indicator = page.inner_text('.btn', timeout=5000)
                match = re.search(r'/\s*(\d+)', page_indicator)
                if match:
                    total_pages = int(match.group(1))
                else:
                    total_pages = 1
            except:
                total_pages = 1
            
            logger.info(f"Extracting {total_pages} pages of content with Playwright...")
            
            output.append("MANUAL CONTENT:")
            output.append("")
            
            # Extract each page
            for page_num in range(1, total_pages + 1):
                logger.debug(f"Extracting page {page_num}/{total_pages}")
                
                # Navigate to specific page
                if page_num == 1:
                    page_url = manual_url
                else:
                    page_url = f"{manual_url}?p={page_num}"
                
                try:
                    page.goto(page_url, wait_until='domcontentloaded', timeout=20000)
                    time.sleep(1)  # Wait for content to render
                    
                    page_text = extract_page_text_playwright(page, page_num)
                    
                    if page_text and len(page_text.strip()) > 5:  # Only add if has meaningful content
                        output.append(f"\n{'='*80}")
                        output.append(f"PAGE {page_num}")
                        output.append('='*80)
                        output.append(page_text)
                    
                    # Small delay between pages
                    if page_num % 5 == 0:
                        time.sleep(0.5)
                        
                except Exception as e:
                    logger.warning(f"Error loading page {page_num}: {e}")
                    continue
            
            output.append("")
            output.append("-" * 80)
            output.append("")
            
            # Get Specifications
            try:
                page.goto(manual_url, wait_until='domcontentloaded', timeout=20000)
                time.sleep(1)
                
                specs_section = page.query_selector('#specs')
                if specs_section:
                    output.append("SPECIFICATIONS:")
                    output.append("")
                    
                    tables = page.query_selector_all('#specs table.table')
                    for table in tables:
                        # Try to get heading
                        try:
                            # Find the h5 before this table
                            heading = page.eval_on_selector(
                                f'#{specs_section.get_attribute("id")} h5',
                                '(h5) => h5.textContent'
                            )
                            if heading:
                                output.append(f"\n{heading}")
                                output.append("-" * 40)
                        except:
                            pass
                        
                        # Get table rows
                        rows = table.query_selector_all('tr')
                        for row in rows:
                            cells = row.query_selector_all('td')
                            if len(cells) >= 2:
                                key = cells[0].inner_text().strip()
                                value = cells[1].inner_text().strip()
                                if key and value:
                                    output.append(f"  {key:.<45} {value}")
                    
                    output.append("")
                    output.append("-" * 80)
                    output.append("")
            except:
                pass
            
            # Get FAQs
            try:
                faq_items = page.query_selector_all('.faq-item')
                if faq_items:
                    output.append("FREQUENTLY ASKED QUESTIONS:")
                    output.append("")
                    
                    for idx, faq in enumerate(faq_items, 1):
                        try:
                            question = faq.query_selector('h4').inner_text()
                            answer = faq.query_selector('[itemprop="text"]').inner_text()
                            
                            output.append(f"Q{idx}: {question}")
                            output.append(f"A{idx}: {answer}")
                            output.append("")
                        except:
                            pass
            except:
                pass
            
            browser.close()
            
            # Combine all sections
            full_text = '\n'.join(output)
            # Clean up excessive whitespace
            full_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', full_text)
            
            return full_text
            
    except Exception as e:
        logger.error(f"Error extracting text with Playwright from {manual_url}: {e}")
        return None

def save_manual_text_playwright(manual_info: dict, category: str, format: str = 'txt') -> bool:
    """
    Extract and save manual text using Playwright
    
    Args:
        manual_info: Dictionary with manual information
        category: 'laptops' or 'desktops'
        format: 'txt' or 'md'
    
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
        filename = f"{brand}_{model}_{pages}pages.{format}"
    else:
        filename = f"{brand}_{model}.{format}"
    
    filename = sanitize_filename(filename)
    output_path = output_dir / filename
    
    # Check if already exists
    if output_path.exists():
        logger.info(f"File already exists: {output_path.name}")
        return True
    
    # Extract text
    logger.info(f"Extracting text with Playwright: {output_path.name}")
    text_content = extract_manual_text_playwright(manual_info['url'])
    
    if not text_content or len(text_content) < 100:
        logger.error(f"Failed to extract sufficient text from {manual_info['url']}")
        return False
    
    # Save to file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        logger.info(f"Successfully saved: {output_path.name} ({len(text_content)} chars)")
        
        # Polite delay
        time.sleep(config.REQUEST_DELAY)
        return True
        
    except Exception as e:
        logger.error(f"Error saving file {output_path}: {e}")
        return False



