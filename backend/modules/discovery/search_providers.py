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
    """Zero-credential fallback search provider using public DuckDuckGo endpoints."""

    def search(self, query: str, limit: int = 5, source_type: str = "webpage") -> List[SearchResult]:
        results: List[SearchResult] = []
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        # Strategy 1: lite.duckduckgo.com via POST (most resilient against anti-bot 202 challenges)
        try:
            with httpx.Client(timeout=12.0, follow_redirects=True) as client:
                resp = client.post(
                    "https://lite.duckduckgo.com/lite/",
                    data={"q": query},
                    headers=headers
                )
                if resp.status_code == 200 and "result-link" in resp.text:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    links = soup.select(".result-link")
                    snippets = soup.select(".result-snippet")

                    for idx, link_elem in enumerate(links):
                        title = link_elem.get_text(strip=True)
                        raw_href = link_elem.get("href", "")
                        clean_url = self._extract_clean_url(raw_href)
                        if not clean_url or not title:
                            continue

                        snippet = ""
                        if idx < len(snippets):
                            snippet = snippets[idx].get_text(strip=True)

                        results.append(SearchResult(
                            title=title,
                            url=canonicalize_url(clean_url),
                            snippet=snippet,
                            source_type=source_type
                        ))
                        if len(results) >= limit:
                            return results
        except Exception as e:
            logger.debug(f"DuckDuckGo lite search error for '{query}': {e}")

        if results:
            return results

        # Strategy 2: html.duckduckgo.com fallback
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for item in soup.select(".result"):
                        title_elem = item.select_one(".result__title a")
                        snippet_elem = item.select_one(".result__snippet")
                        if not title_elem:
                            continue

                        title = title_elem.get_text(strip=True)
                        raw_href = title_elem.get("href", "")
                        clean_url = self._extract_clean_url(raw_href)
                        if not clean_url:
                            continue

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

    @staticmethod
    def _extract_clean_url(raw_href: str) -> str:
        if not raw_href:
            return ""
        if "uddg=" in raw_href:
            parsed = urllib.parse.urlparse(raw_href)
            qs = urllib.parse.parse_qs(parsed.query)
            if "uddg" in qs:
                return qs["uddg"][0]
        if raw_href.startswith("//"):
            return f"https:{raw_href}"
        return raw_href


class SearchProviderFactory:
    @staticmethod
    def get_provider() -> BaseSearchProvider:
        if settings.EXA_API_KEY:
            return ExaSearchProvider()
        return DuckDuckGoSearchProvider()

