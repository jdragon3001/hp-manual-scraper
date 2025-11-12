"""
Extract manual content as formatted text/markdown from manua.ls HTML pages
This is much faster than PDF generation via browser automation
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional
import config
from src.utils import setup_logging, sanitize_filename
from pathlib import Path
import time
import re

logger = setup_logging(__name__)

def clean_text(text: str) -> str:
    """Clean and format text"""
    # Remove excessive whitespace
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    # Remove leading/trailing whitespace from lines
    lines = [line.rstrip() for line in text.split('\n')]
    return '\n'.join(lines).strip()

def get_total_pages(manual_url: str) -> int:
    """
    Get total number of pages in the manual
    
    Args:
        manual_url: URL of the manual page
    
    Returns:
        Total number of pages
    """
    try:
        response = requests.get(manual_url, headers=config.HEADERS, timeout=config.TIMEOUT)
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Find the page indicator (e.g., "1 / 126")
        page_indicator = soup.find('button', class_='btn')
        if page_indicator:
            text = page_indicator.get_text()
            # Extract "126" from "1 / 126"
            match = re.search(r'/\s*(\d+)', text)
            if match:
                return int(match.group(1))
        
        # Fallback: check pagination
        max_page = 1
        pagination = soup.find_all('a', href=lambda x: x and '?p=' in x)
        for link in pagination:
            href = link.get('href')
            match = re.search(r'\?p=(\d+)', href)
            if match:
                page_num = int(match.group(1))
                max_page = max(max_page, page_num)
        
        return max_page
        
    except Exception as e:
        logger.error(f"Error getting page count: {e}")
        return 1

def extract_page_text(manual_url: str, page_num: int) -> str:
    """
    Extract text from a single page of the manual
    
    Args:
        manual_url: Base URL of the manual
        page_num: Page number to extract
    
    Returns:
        Text content of the page
    """
    try:
        # Construct page URL
        if page_num == 1:
            page_url = manual_url
        else:
            page_url = f"{manual_url}?p={page_num}"
        
        response = requests.get(page_url, headers=config.HEADERS, timeout=config.TIMEOUT)
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract text from the viewer page
        viewer_page = soup.find('div', class_='viewer-page')
        if not viewer_page:
            return ""
        
        # Get all text elements
        text_elements = viewer_page.find_all('div', class_=lambda x: x and 't m' in x if x else False)
        
        page_lines = []
        for elem in text_elements:
            text = elem.get_text(strip=True)
            if text:
                page_lines.append(text)
        
        return '\n'.join(page_lines) if page_lines else ""
        
    except Exception as e:
        logger.error(f"Error extracting page {page_num}: {e}")
        return ""

def extract_manual_text(manual_url: str) -> Optional[str]:
    """
    Extract complete manual text content from ALL pages
    
    Args:
        manual_url: URL of the manual page
    
    Returns:
        Complete formatted text content or None
    """
    try:
        response = requests.get(manual_url, headers=config.HEADERS, timeout=config.TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Build the text document
        output = []
        
        # Get title
        title = soup.find('h1')
        if title:
            output.append("=" * 80)
            output.append(title.get_text(strip=True).upper())
            output.append("=" * 80)
            output.append("")
        
        # Get product info
        subtitle = soup.find('div', class_='manual__subtitle')
        if subtitle:
            info_text = subtitle.get_text(separator=' | ', strip=True)
            output.append(info_text)
            output.append("-" * 80)
            output.append("")
        
        # Get description
        description = soup.find('div', class_='manual__description')
        if description:
            desc_text = description.get_text(separator='\n', strip=True)
            output.append("DESCRIPTION:")
            output.append(desc_text)
            output.append("")
            output.append("-" * 80)
            output.append("")
        
        # Get Table of Contents
        toc = soup.find('div', class_='toc__container')
        if toc:
            output.append("TABLE OF CONTENTS:")
            output.append("")
            toc_items = toc.find_all('a')
            for item in toc_items:
                page = item.get('data-page', '')
                text = item.get_text(strip=True)
                if text:
                    output.append(f"  Page {page:>3}: {text}")
            output.append("")
            output.append("-" * 80)
            output.append("")
        
        # Extract ALL pages of the manual
        total_pages = get_total_pages(manual_url)
        logger.info(f"Extracting {total_pages} pages of content...")
        
        output.append("MANUAL CONTENT:")
        output.append("")
        
        for page_num in range(1, total_pages + 1):
            logger.debug(f"Extracting page {page_num}/{total_pages}")
            page_text = extract_page_text(manual_url, page_num)
            if page_text:
                output.append(f"\n{'='*80}")
                output.append(f"PAGE {page_num}")
                output.append('='*80)
                output.append(page_text)
            
            # Small delay to be polite
            if page_num % 10 == 0:
                time.sleep(0.5)
        
        output.append("")
        output.append("-" * 80)
        output.append("")
        
        # Get Specifications
        specs_section = soup.find('div', id='specs')
        if specs_section:
            output.append("SPECIFICATIONS:")
            output.append("")
            
            # Find all spec tables
            tables = specs_section.find_all('table', class_='table')
            for table in tables:
                # Get the heading
                heading = table.find_previous('h5')
                if heading:
                    heading_text = heading.get_text(strip=True)
                    output.append(f"\n{heading_text}")
                    output.append("-" * 40)
                
                # Get table rows
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            output.append(f"  {key:.<45} {value}")
            
            output.append("")
            output.append("-" * 80)
            output.append("")
        
        # Get FAQs
        faq_items = soup.find_all('div', class_='faq-item')
        if faq_items:
            output.append("FREQUENTLY ASKED QUESTIONS:")
            output.append("")
            
            for idx, faq in enumerate(faq_items, 1):
                question_elem = faq.find('h4')
                answer_elem = faq.find('div', itemprop='text')
                
                if question_elem and answer_elem:
                    question = question_elem.get_text(strip=True)
                    answer = answer_elem.get_text(strip=True)
                    
                    output.append(f"Q{idx}: {question}")
                    output.append(f"A{idx}: {answer}")
                    output.append("")
        
        # Combine all sections
        full_text = '\n'.join(output)
        return clean_text(full_text)
        
    except Exception as e:
        logger.error(f"Error extracting text from {manual_url}: {e}")
        return None

def save_manual_text(manual_info: dict, category: str, format: str = 'txt') -> bool:
    """
    Extract and save manual text
    
    Args:
        manual_info: Dictionary with manual information
        category: 'laptops' or 'desktops'
        format: 'txt' or 'md' (markdown)
    
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
    logger.info(f"Extracting text from: {output_path.name}")
    text_content = extract_manual_text(manual_info['url'])
    
    if not text_content:
        logger.error(f"Failed to extract text from {manual_info['url']}")
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

