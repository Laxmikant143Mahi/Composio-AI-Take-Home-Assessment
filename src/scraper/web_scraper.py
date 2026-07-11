import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from duckduckgo_search import DDGS
from src.config import USER_AGENT, SCRAPE_TIMEOUT, MAX_RETRIES, BACKOFF_FACTOR
from src.utils.logger import setup_logger
from src.utils.helpers import clean_html_content

logger = setup_logger("scraper.web_scraper")

class WebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        # Attempt to set up connection retry strategy
        from urllib3.util import Retry
        from requests.adapters import HTTPAdapter
        retries = Retry(
            total=MAX_RETRIES,
            backoff_factor=BACKOFF_FACTOR,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.playwright_browser = None

    def search_documentation(self, app_name: str, query_type: str = "api_docs") -> List[str]:
        """
        Queries the discovery layer (DuckDuckGo search) to find developer resources.
        
        query_type can be 'api_docs' or 'dev_portal'.
        """
        if query_type == "api_docs":
            query = f"{app_name} developer api documentation official"
        elif query_type == "dev_portal":
            query = f"{app_name} developer portal sign up console"
        else:
            query = f"{app_name} official documentation"
            
        logger.info(f"Querying discovery layer for: '{query}'")
        urls = []
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                for r in results:
                    url = r.get("href")
                    if url:
                        # Exclude app stores, social media, general blogs
                        ignore_patterns = [
                            "play.google.com", "apps.microsoft.com", "apps.apple.com", 
                            "wikipedia.org", "youtube.com", "twitter.com", "facebook.com", 
                            "linkedin.com", "medium.com", "github.com/apps/"
                        ]
                        if not any(pat in url.lower() for pat in ignore_patterns):
                            urls.append(url)
            urls = urls[:3]  # Keep top 3 clean URLs
            logger.info(f"Found {len(urls)} discovery results for '{app_name}' ({query_type})")
        except Exception as e:
            logger.warning(f"Discovery search failed for query '{query}': {e}. Falling back to default URL construction.")
            # Fallback to standard URL construction if DDG search is rate-limited or fails
            sanitized = app_name.lower().replace(" ", "").strip()
            if query_type == "api_docs":
                urls = [f"https://docs.{sanitized}.com", f"https://developer.{sanitized}.com"]
            else:
                urls = [f"https://developer.{sanitized}.com", f"https://dashboard.{sanitized}.com"]
        return urls

    def fetch_page_content(self, url: str, force_playwright: bool = False) -> str:
        """
        Fetches web page content. First attempts requests (fast pathway).
        Falls back to Playwright if JavaScript rendering is requested/required.
        """
        if not url:
            return ""
            
        if force_playwright:
            return self._fetch_via_playwright(url)
            
        logger.debug(f"Fetching page content via requests: {url}")
        try:
            response = self.session.get(url, timeout=SCRAPE_TIMEOUT)
            if response.status_code == 200:
                return response.text
            elif response.status_code in [403, 401] or "cloudflare" in response.text.lower():
                logger.info(f"Requests returned status {response.status_code} or triggered protection for {url}. Attempting Playwright fallback.")
                return self._fetch_via_playwright(url)
            else:
                logger.warning(f"Requests returned code {response.status_code} for {url}")
                return ""
        except requests.RequestException as e:
            logger.warning(f"Requests fetch failed for {url}: {e}. Retrying via Playwright.")
            return self._fetch_via_playwright(url)

    def ping_url(self, url: str) -> int:
        """Pings a URL and returns the HTTP status code. Returns 0 if unreachable."""
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        headers = {"User-Agent": USER_AGENT}
        try:
            # Send a HEAD request first (faster) without session retries to prevent connection hangs
            response = requests.head(url, headers=headers, timeout=3.0, allow_redirects=True, verify=False)
            if response.status_code in [405, 403]:  # Some sites reject HEAD requests
                response = requests.get(url, headers=headers, timeout=3.0, allow_redirects=True, verify=False)
            return response.status_code
        except Exception:
            try:
                # Retry with GET in case HEAD failed due to network quirks
                response = requests.get(url, headers=headers, timeout=3.0, allow_redirects=True, verify=False)
                return response.status_code
            except Exception as e:
                logger.debug(f"Failed to ping {url}: {e}")
                return 0

    def _fetch_via_playwright(self, url: str) -> str:
        """Attempts to render the page using headless Playwright browser."""
        logger.info(f"Launching Playwright fallback browser for {url}")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.warning("Playwright is not installed. Returning empty content.")
            return ""
            
        try:
            with sync_playwright() as p:
                # Use a try block to handle browsers not being downloaded
                try:
                    browser = p.chromium.launch(headless=True)
                except Exception as browser_err:
                    logger.warning(f"Playwright chromium not downloaded or failed to launch: {browser_err}. Attempting requests fallback.")
                    return ""
                    
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.goto(url, timeout=int(SCRAPE_TIMEOUT * 1000))
                # Wait briefly for dynamic elements
                time.sleep(2)
                content = page.content()
                browser.close()
                return content
        except Exception as e:
            logger.error(f"Playwright rendering failed for {url}: {e}")
            return ""
