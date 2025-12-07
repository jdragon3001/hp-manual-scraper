"""
Main scraper logic for manua.ls
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import config
from src.utils import setup_logging, load_progress, save_progress
from src.pdf_extractor import extract_manual_info
from src.playwright_text_extractor import save_manual_text_playwright
from src.robust_extractor import save_manual_robust

logger = setup_logging(__name__)

class ManualscrScraper:
    """Scraper for manua.ls manuals"""
    
    def __init__(self):
        self.progress = load_progress()
        self.session = requests.Session()
        self.session.headers.update(config.HEADERS)
    
    def get_manual_links_from_page(self, url: str) -> List[str]:
        """
        Extract all manual links from a category page
        
        Args:
            url: Category page URL
        
        Returns:
            List of manual page URLs
        """
        try:
            response = self.session.get(url, timeout=config.TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            manual_links = []
            
            # Find all manual links - they typically link to individual manual pages
            # Looking for links in the manuals section
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                
                # Manual links typically follow pattern: /brand/model/manual
                if href and '/manual' in href and href.count('/') >= 3:
                    full_url = href if href.startswith('http') else f"https://www.manua.ls{href}"
                    if full_url not in manual_links:
                        manual_links.append(full_url)
            
            logger.info(f"Found {len(manual_links)} manual links on {url}")
            return manual_links
            
        except Exception as e:
            logger.error(f"Error getting manual links from {url}: {e}")
            return []
    
    def get_total_pages(self, category_url: str) -> int:
        """
        Get total number of pagination pages
        
        Args:
            category_url: Base category URL
        
        Returns:
            Total number of pages
        """
        # Hardcoded page counts based on known totals
        # Laptops: 15,193 manuals / 100 per page = 152 pages (rounded to 151)
        # Desktops: 5,111 manuals / 100 per page = 52 pages (rounded to 51)
        if 'laptops' in category_url:
            logger.info(f"Using hardcoded 151 pages for laptops (15,193 manuals)")
            return 151
        elif 'desktops' in category_url:
            logger.info(f"Using hardcoded 51 pages for desktops (5,111 manuals)")
            return 51
        
        # Fallback to dynamic detection if needed
        try:
            import re
            response = self.session.get(category_url, timeout=config.TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Find pagination links (uses ?p= not ?page=)
            pagination = soup.find_all('a', href=lambda x: x and '?p=' in x)
            
            max_page = 1
            for link in pagination:
                href = link.get('href')
                if '?p=' in href:
                    try:
                        # Extract page number from ?p=NUMBER
                        match = re.search(r'\?p=(\d+)', href)
                        if match:
                            page_num = int(match.group(1))
                            max_page = max(max_page, page_num)
                    except ValueError:
                        pass
            
            logger.info(f"Found {max_page} pages for {category_url}")
            return max_page
            
        except Exception as e:
            logger.error(f"Error getting page count for {category_url}: {e}")
            return 1
    
    def scrape_category(self, category_url: str, category: str) -> List[Dict]:
        """
        Scrape all manuals from a category (laptops or desktops)
        
        Args:
            category_url: Base URL for the category
            category: 'laptops' or 'desktops'
        
        Returns:
            List of manual information dictionaries
        """
        logger.info(f"Starting scrape of {category} from {category_url}")
        
        # Get total pages
        total_pages = self.get_total_pages(category_url)
        logger.info(f"Will scrape {total_pages} pages for {category}")
        
        all_manual_links = []
        
        # Get manual links from each page
        for page in range(1, total_pages + 1):
            page_url = f"{category_url}?p={page}" if page > 1 else category_url
            logger.info(f"Scraping page {page}/{total_pages}")
            
            manual_links = self.get_manual_links_from_page(page_url)
            all_manual_links.extend(manual_links)
            
            # Polite delay between page requests
            time.sleep(config.REQUEST_DELAY)
        
        logger.info(f"Found total of {len(all_manual_links)} manuals for {category}")
        
        # Filter out already downloaded
        new_links = [link for link in all_manual_links if link not in self.progress[category]]
        logger.info(f"{len(new_links)} new manuals to download for {category}")
        
        return new_links
    
    def download_manual_wrapper(self, manual_url: str, category: str, use_robust: bool = True) -> bool:
        """
        Wrapper to extract info and download a manual as text
        
        Args:
            manual_url: URL of the manual page
            category: 'laptops' or 'desktops'
            use_robust: Use robust extractor with fallbacks (default True)
        
        Returns:
            True if successful
        """
        try:
            # Extract manual information
            manual_info = extract_manual_info(manual_url)
            
            if not manual_info:
                logger.warning(f"Could not extract info from {manual_url}")
                return False
            
            # Add URL to manual_info for text extraction
            manual_info['url'] = manual_url
            
            # Try robust extractor first (with image fallback)
            if use_robust:
                success = save_manual_robust(manual_info, category, format='txt')
            else:
                # Fall back to original Playwright extractor
            success = save_manual_text_playwright(manual_info, category, format='txt')
            
            if success:
                # Update progress
                self.progress[category].add(manual_url)
                save_progress(self.progress)
            
            return success
            
        except Exception as e:
            logger.error(f"Error processing {manual_url}: {e}")
            return False
    
    def download_all_manuals(self, manual_links: List[str], category: str):
        """
        Download all manuals using concurrent downloads
        
        Args:
            manual_links: List of manual page URLs
            category: 'laptops' or 'desktops'
        """
        logger.info(f"Starting download of {len(manual_links)} {category} manuals")
        
        successful = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=config.CONCURRENT_DOWNLOADS) as executor:
            # Submit all download tasks
            future_to_url = {
                executor.submit(self.download_manual_wrapper, url, category): url
                for url in manual_links
            }
            
            # Process completed downloads with progress bar
            with tqdm(total=len(manual_links), desc=f"Downloading {category}") as pbar:
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        if result:
                            successful += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"Error downloading {url}: {e}")
                        failed += 1
                    
                    pbar.update(1)
                    pbar.set_postfix({'Success': successful, 'Failed': failed})
        
        logger.info(f"Completed {category}: {successful} successful, {failed} failed")
    
    def run(self, categories: List[str] = ['laptops', 'desktops']):
        """
        Run the scraper for specified categories
        
        Args:
            categories: List of categories to scrape ('laptops', 'desktops')
        """
        logger.info("=" * 50)
        logger.info("Starting manua.ls scraper")
        logger.info("=" * 50)
        
        for category in categories:
            if category == 'laptops':
                category_url = config.LAPTOP_URL
            elif category == 'desktops':
                category_url = config.DESKTOP_URL
            else:
                logger.error(f"Unknown category: {category}")
                continue
            
            logger.info(f"\nProcessing category: {category}")
            logger.info("-" * 50)
            
            # Get all manual links
            manual_links = self.scrape_category(category_url, category)
            
            if not manual_links:
                logger.info(f"No new manuals to download for {category}")
                continue
            
            # Download all manuals
            self.download_all_manuals(manual_links, category)
        
        logger.info("=" * 50)
        logger.info("Scraper completed!")
        logger.info("=" * 50)

def main():
    """Main entry point"""
    scraper = ManualscrScraper()
    scraper.run()

if __name__ == '__main__':
    main()

