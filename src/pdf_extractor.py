"""
PDF URL extraction from manual pages
"""
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
import config
from src.utils import setup_logging

logger = setup_logging(__name__)

def extract_pdf_url(manual_url: str) -> Optional[str]:
    """
    Extract PDF download URL from a manual page
    
    Args:
        manual_url: URL of the manual page
    
    Returns:
        PDF download URL or None if not found
    """
    try:
        response = requests.get(manual_url, headers=config.HEADERS, timeout=config.TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Strategy 1: Look in JavaScript/script tags for PDF URLs
        # manua.ls embeds the PDF URL in scripts
        scripts = soup.find_all('script')
        for script in scripts:
            script_content = script.string
            if script_content:
                import re
                # Look for PDF URLs in script content
                urls = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', script_content, re.IGNORECASE)
                for url in urls:
                    # Filter out generic or non-specific URLs
                    if 'manual' in url and ('pdfmanualer' in url or 'manua.ls' in url):
                        if not url.startswith('http'):
                            url = 'https://' + url.lstrip('/')
                        # Convert pdfmanualer.dk URL to manua.ls format
                        if 'pdfmanualer.dk' in url:
                            url = url.replace('pdfmanualer.dk', 'manua.ls')
                        return url
        
        # Strategy 2: Look for direct PDF link
        pdf_link = soup.find('a', href=lambda x: x and x.endswith('.pdf'))
        if pdf_link:
            pdf_url = pdf_link.get('href')
            if not pdf_url.startswith('http'):
                pdf_url = 'https://www.manua.ls' + pdf_url
            return pdf_url
        
        # Strategy 3: Look for embedded PDF viewer (iframe or object)
        iframe = soup.find('iframe', src=lambda x: x and '.pdf' in x)
        if iframe:
            pdf_url = iframe.get('src')
            if not pdf_url.startswith('http'):
                pdf_url = 'https://www.manua.ls' + pdf_url
            return pdf_url
        
        # Strategy 4: Look for object/embed tags
        obj = soup.find('object', data=lambda x: x and '.pdf' in x)
        if obj:
            pdf_url = obj.get('data')
            if not pdf_url.startswith('http'):
                pdf_url = 'https://www.manua.ls' + pdf_url
            return pdf_url
        
        # Strategy 5: Look in meta tags
        meta_pdf = soup.find('meta', property='og:url', content=lambda x: x and '.pdf' in x)
        if meta_pdf:
            return meta_pdf.get('content')
        
        # Strategy 6: Look for download button or link
        download_btn = soup.find('a', class_=lambda x: x and 'download' in x.lower() if x else False)
        if download_btn:
            pdf_url = download_btn.get('href')
            if pdf_url and not pdf_url.startswith('http'):
                pdf_url = 'https://www.manua.ls' + pdf_url
            return pdf_url
        
        logger.warning(f"Could not find PDF URL in {manual_url}")
        return None
        
    except Exception as e:
        logger.error(f"Error extracting PDF from {manual_url}: {e}")
        return None

def extract_manual_info(manual_url: str) -> Optional[Dict[str, str]]:
    """
    Extract manual information (brand, model, pages) from manual page
    
    Args:
        manual_url: URL of the manual page
    
    Returns:
        Dictionary with manual info or None
    """
    try:
        response = requests.get(manual_url, headers=config.HEADERS, timeout=config.TIMEOUT)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'lxml')
        
        info = {
            'url': manual_url,
            'brand': '',
            'model': '',
            'pages': '',
            'pdf_url': ''
        }
        
        # Extract title (usually "BRAND MODEL manual")
        title = soup.find('h1')
        if title:
            title_text = title.get_text(strip=True)
            # Remove " manual" suffix
            if ' manual' in title_text:
                title_text = title_text.replace(' manual', '')
            
            # Try to split into brand and model
            parts = title_text.split(' ', 1)
            if len(parts) >= 1:
                info['brand'] = parts[0]
            if len(parts) >= 2:
                info['model'] = parts[1]
        
        # Extract page count
        pages_elem = soup.find(text=lambda x: x and 'pages' in x.lower())
        if pages_elem:
            import re
            match = re.search(r'(\d+)\s*pages?', pages_elem, re.IGNORECASE)
            if match:
                info['pages'] = match.group(1)
        
        # Extract PDF URL
        info['pdf_url'] = extract_pdf_url(manual_url)
        
        return info
        
    except Exception as e:
        logger.error(f"Error extracting manual info from {manual_url}: {e}")
        return None

