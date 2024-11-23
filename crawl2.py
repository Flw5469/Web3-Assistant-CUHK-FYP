import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import json
import time
from concurrent.futures import ThreadPoolExecutor
import logging
import datetime

class WebCrawler:
    def __init__(self, start_url, allowed_domains=None, max_depth=2, max_pages=100, datetime = datetime.datetime.now()):
        self.start_url = start_url
        self.allowed_domains = allowed_domains or [urlparse(start_url).netloc]
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.datetime = datetime
        self.visited_urls = set()
        self.data = []
        self.session = requests.Session()
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # # Set headers to mimic a browser
        # self.headers = {
        #     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        # }

        self.headers = {
          "authority": "www.google.com",
          "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
          "accept-language": "en-US,en;q=0.9",
          "cache-control": "max-age=0",
          "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
          # add more headers as needed
        }

    def is_valid_url(self, url):
        """Check if URL is valid and belongs to allowed domains"""
        try:
            parsed = urlparse(url)
            return any(domain in parsed.netloc for domain in self.allowed_domains)
        except:
            return False

    def get_page_content(self, url):
        """Fetch page content with error handling"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return None

    def extract_page_data(self, url, html):
        """Extract relevant data from the page"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            paragraphs = soup.find_all('p')

            # Extract basic page information
            data = {
                'URL': url,
                'news_title': soup.title.string if soup.title else None,
                'news_content': ' '.join(p.get_text(strip=True) for p in paragraphs),
                'links': [],
                'date' : str(self.datetime)
            }
            
            if data["news_content"]=="":
                data['news_content'] = soup.get_text(strip=True)

            # Extract all links
            for link in soup.find_all('a', href=True):
                href = link.get('href')
                absolute_url = urljoin(url, href)
                if self.is_valid_url(absolute_url):
                    data['links'].append(absolute_url)
            
            return data
        except Exception as e:
            self.logger.error(f"Error parsing {url}: {str(e)}")
            return None

    def crawl_page(self, url, depth=0):
        """Crawl a single page and its links up to max_depth"""
        if (
            depth >= self.max_depth or
            url in self.visited_urls or
            len(self.visited_urls) >= self.max_pages or
            not self.is_valid_url(url)
        ):
            return

        self.visited_urls.add(url)
        self.logger.info(f"Crawling: {url} (Depth: {depth})")

        # Get page content
        html = self.get_page_content(url)
        if not html:
            return

        # Extract data from the page
        page_data = self.extract_page_data(url, html)
        if page_data:
            self.data.append(page_data)

        # Crawl linked pages
        with ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(
                lambda link: self.crawl_page(link, depth + 1),
                page_data['links'] if page_data else []
            )

    def crawl(self):
        """Start the crawling process"""
        start_time = time.time()
        self.logger.info(f"Starting crawl from: {self.start_url}")
        
        self.crawl_page(self.start_url)
        
        duration = time.time() - start_time
        self.logger.info(f"Crawl completed. Pages crawled: {len(self.visited_urls)}")
        self.logger.info(f"Time taken: {duration:.2f} seconds")

    def save_results(self, filename='crawl_result.json'):
        """Save crawled data to a JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Results saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")

def main(url="https://www.cointrust.com/", id = 1, depth=1, datetime = datetime.datetime.now()):
    # Example usage
    start_url = url  # Replace with your target URL
    crawler = WebCrawler(
        start_url=start_url,
        max_depth=depth,
        max_pages=80,
        datetime = datetime
    )
    
    crawler.crawl()

    crawler.save_results(f"./crawl_result/crawl_result_{id}.json")

if __name__ == "__main__":
    main()