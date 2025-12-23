import scrapy
from scrapy.crawler import CrawlerProcess
from typing import List, Dict, Optional
from urllib.parse import urljoin
import json
from bs4 import BeautifulSoup  # type: ignore
from readability import Document
def process_html(html: str, url: Optional[str] = None) -> Dict:
    """Extract structured data from raw HTML.

    Tries to use readability, falls back to BeautifulSoup-only heuristics.
    Returns a dict with keys: title, meta_description, main_text, json_ld, top_images, links, raw_html
    """
    title = None
    main_text = None
    content_html = None
    doc = Document(html)
    # Always use BeautifulSoup full-page parsing
    soup = BeautifulSoup(html, "html.parser")
    for s in soup(["script", "style", "noscript"]):
        s.decompose()
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    main_text = soup.get_text(separator="\n", strip=True)

    # Extract meta description
    meta_description = None
    desc = soup.select_one("meta[name=description]") or soup.select_one("meta[property='og:description']")
    if desc:
        meta_description = desc.get("content")

    # JSON-LD
    json_ld = []
    try:
        for tag in soup.find_all("script", type="application/ld+json"):
            try:
                text = tag.string or ""
                parsed = json.loads(text)
                json_ld.append(parsed)
            except Exception:
                continue
    except Exception:
        json_ld = []

    # Images and links
    images = []
    links = []
    try:
        for img in soup.find_all("img", src=True):
            images.append(urljoin(url or "", img["src"]))
        for a in soup.find_all("a", href=True):
            links.append(urljoin(url or "", a["href"]))
    except Exception:
        pass

    return {
        "title": title,
        "meta_description": meta_description,
        "main_text": main_text,
        "json_ld": json_ld,
        "top_images": images[:10],
        "links": links,
        "raw_html": html,
    }

class URLSpider(scrapy.Spider):
    name = "url_spider"

    def __init__(self, start_urls: List[str], results: Optional[List[Dict]] = None, *args, **kwargs):
        super(URLSpider, self).__init__(*args, **kwargs)
        self.start_urls = start_urls
        self.results = results if results is not None else []

    def parse(self, response):
        # Debug print so we can see when parse runs
        print(f"[url_spider] fetched {response.url} (status={getattr(response, 'status', 'unknown')})")
        page_content = response.text
        extracted = process_html(page_content, response.url)
        record = {
            "url": response.url,
            "status": getattr(response, 'status', None),
        }
        record.update(extracted)
        self.results.append(record)

    def start_requests(self):
        # Explicitly create requests so we can set headers and avoid filtering
        ua = getattr(self, 'user_agent', None) or self.settings.get('USER_AGENT')
        headers = {"User-Agent": ua} if ua else None
        for url in self.start_urls:
            if headers:
                yield scrapy.Request(url, callback=self.parse, dont_filter=True, headers=headers)
            else:
                yield scrapy.Request(url, callback=self.parse, dont_filter=True)

    
def scrape_urls(urls: List[str]) -> List[Dict[str, str]]:
    """Scrape the given list of URLs and return their content."""
    process = CrawlerProcess(settings={
        "LOG_LEVEL": "ERROR",
        "USER_AGENT": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_TIMEOUT": 15,
    })
    # Pass the spider class and provide start_urls as a kwarg
    results: List[Dict[str, str]] = []
    process.crawl(URLSpider, start_urls=urls, results=results)
    process.start()  # the script will block here until the crawling is finished

    return results

if __name__ == "__main__":
    test_urls = [
        "https://finance.yahoo.com/news/nvidia-latest-2-billion-deal-153729086.html"
    ]
    scraped_data = scrape_urls(test_urls)
    for data in scraped_data:
        snippet = (data.get("main_text") or data.get("raw_html") or "")
        print(f"URL: {data.get('url')}\nContent Snippet: {snippet}...\n")