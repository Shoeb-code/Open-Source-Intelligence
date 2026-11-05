import abc
import urllib.parse
from typing import List, Optional
from pydantic import BaseModel
import httpx
from bs4 import BeautifulSoup
from backend.config import settings
from backend.utils.logger import logger
from backend.utils.url_validator import canonicalize_url


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: Optional[str] = None
    published_date: Optional[str] = None
    source_type: str = "webpage"


class BaseSearchProvider(abc.ABC):
    @abc.abstractmethod
    def search(self, query: str, limit: int = 5, source_type: str = "webpage") -> List[SearchResult]:
        """Executes a search query and returns normalized search results."""
        pass


class ExaSearchProvider(BaseSearchProvider):
    """Exa AI search provider for high-relevance web and media discovery."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.EXA_API_KEY
        self.base_url = "https://api.exa.ai/search"

    def search(self, query: str, limit: int = 5, source_type: str = "webpage") -> List[SearchResult]:
        if not self.api_key:
            logger.warning("Exa API key not configured. Falling back to DuckDuckGo search.")
            return DuckDuckGoSearchProvider().search(query, limit, source_type)

        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "query": query,
            "numResults": limit,
            "useAutoprompt": True
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                resp = client.post(self.base_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                results = []
                for item in data.get("results", []):
                    results.append(SearchResult(
                        title=item.get("title") or "Web Result",
                        url=canonicalize_url(item.get("url")),
                        snippet=item.get("text") or item.get("snippet"),
                        published_date=item.get("publishedDate"),
                        source_type=source_type
                    ))
                return results
        except Exception as e:
            logger.error(f"Exa search failed for query '{query}': {e}. Falling back to DuckDuckGo.")
            return DuckDuckGoSearchProvider().search(query, limit, source_type)


class DuckDuckGoSearchProvider(BaseSearchProvider):
    """Zero-credential fallback search provider using public html endpoint."""

    def search(self, query: str, limit: int = 5, source_type: str = "webpage") -> List[SearchResult]:
        results: List[SearchResult] = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code != 200:
                    return results

                soup = BeautifulSoup(resp.text, "html.parser")
                for item in soup.select(".result"):
                    title_elem = item.select_one(".result__title a")
                    snippet_elem = item.select_one(".result__snippet")
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    raw_href = title_elem.get("href", "")
                    
                    # DuckDuckGo wraps URLs in /l/?uddg=...
                    clean_url = raw_href
                    if "uddg=" in raw_href:
                        parsed = urllib.parse.urlparse(raw_href)
                        qs = urllib.parse.parse_qs(parsed.query)
                        if "uddg" in qs:
                            clean_url = qs["uddg"][0]

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                    results.append(SearchResult(
                        title=title,
                        url=canonicalize_url(clean_url),
                        snippet=snippet,
                        source_type=source_type
                    ))
                    if len(results) >= limit:
                        break
        except Exception as e:
            logger.warning(f"DuckDuckGo search error for '{query}': {e}")
        return results


class SearchProviderFactory:
    @staticmethod
    def get_provider() -> BaseSearchProvider:
        if settings.EXA_API_KEY:
            return ExaSearchProvider()
        return DuckDuckGoSearchProvider()

