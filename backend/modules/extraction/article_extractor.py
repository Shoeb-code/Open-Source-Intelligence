from typing import Optional, Tuple
import httpx
from bs4 import BeautifulSoup
from backend.config import settings
from backend.utils.logger import logger
from backend.utils.text_cleaner import clean_text


class ArticleExtractor:
    """Extracts readable article or webpage content using Firecrawl or resilient HTML parsing."""

    @staticmethod
    def extract_with_firecrawl(url: str) -> Optional[str]:
        if not settings.FIRECRAWL_API_KEY:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
                "Content-Type": "application/json"
            }
            with httpx.Client(timeout=20.0) as client:
                res = client.post(
                    "https://api.firecrawl.dev/v0/scrape",
                    headers=headers,
                    json={"url": url, "pageOptions": {"onlyMainContent": True}}
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("data", {}).get("markdown") or data.get("data", {}).get("content")
        except Exception as e:
            logger.warning(f"Firecrawl scrape failed for {url}: {e}")
        return None

    @classmethod
    def extract_article_text(cls, url: str) -> Tuple[Optional[str], str]:
        """
        Returns (content_text, extraction_status).
        Status is SUCCESS, RESTRICTED, or FAILED.
        """
        # 1. Try Firecrawl if API key configured
        if settings.FIRECRAWL_API_KEY:
            fc_content = cls.extract_with_firecrawl(url)
            if fc_content:
                return clean_text(fc_content), "SUCCESS"

        # 2. Resilient standard HTTP + BeautifulSoup extraction
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        try:
            with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code in (401, 403, 429):
                    logger.warning(f"Extraction restricted (HTTP {resp.status_code}) for URL: {url}")
                    return None, "RESTRICTED"
                if resp.status_code != 200:
                    return None, "FAILED"

                soup = BeautifulSoup(resp.text, "lxml")

                # Remove non-content tags
                for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside"]):
                    tag.decompose()

                # Prefer article tag or main tag if present
                main_elem = soup.find("article") or soup.find("main") or soup.find("body")
                if not main_elem:
                    return None, "FAILED"

                # Extract paragraph texts
                paragraphs = [p.get_text(strip=True) for p in main_elem.find_all(["p", "h1", "h2", "h3", "li"])]
                text = "\n\n".join([p for p in paragraphs if len(p) > 20])
                if not text:
                    text = main_elem.get_text(separator="\n", strip=True)

                cleaned = clean_text(text)
                return (cleaned, "SUCCESS") if len(cleaned) > 50 else (cleaned, "SUCCESS")

        except httpx.HTTPError as e:
            logger.warning(f"Network error extracting {url}: {e}")
            return None, "RESTRICTED"
        except Exception as e:
            logger.error(f"Unexpected error extracting {url}: {e}")
            return None, "FAILED"

