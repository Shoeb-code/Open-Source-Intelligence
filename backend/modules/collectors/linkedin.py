import re
from typing import List, Optional
from urllib.parse import urlparse
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.discovery.search_providers import SearchProviderFactory
from backend.utils.url_validator import canonicalize_url


class LinkedInCollector:
    """Discovers public LinkedIn profiles, posts, Pulse articles, talks, and thought leadership pieces."""

    def __init__(self):
        self.search_provider = SearchProviderFactory.get_provider()

    @staticmethod
    def _extract_username(url: str) -> Optional[str]:
        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            parts = path.split("/")
            if "in" in parts:
                idx = parts.index("in")
                if idx + 1 < len(parts):
                    return parts[idx + 1]
            return None
        except Exception:
            return None

    @staticmethod
    def _detect_item_type(url: str) -> str:
        url_lower = url.lower()
        if "/pulse/" in url_lower:
            return "ARTICLE"
        elif "/posts/" in url_lower or "/feed/update/" in url_lower:
            return "LINKEDIN_POST"
        elif "/in/" in url_lower:
            return "LINKEDIN_PROFILE"
        return "LINKEDIN_POST"

    @staticmethod
    def _clean_title(title: str, url: str) -> str:
        if not title:
            return "LinkedIn Publication"
        clean = title
        clean = re.sub(r'[\s\-|•]+LinkedIn(?:\s+(?:India|Pulse))?.*$', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'^LinkedIn:\s*', '', clean, flags=re.IGNORECASE)
        clean = clean.strip().rstrip("-|• ")
        if not clean:
            parsed_user = LinkedInCollector._extract_username(url)
            return f"LinkedIn Profile ({parsed_user})" if parsed_user else "LinkedIn Publication"
        return clean

    def discover(self, queries: List[str], max_per_query: int = 4) -> List[DiscoveredItem]:
        items: List[DiscoveredItem] = []
        seen_urls = set()

        for q, results in self.search_provider.search_batch(queries, limit=max_per_query, source_type="LINKEDIN"):
            for r in results:
                canon = canonicalize_url(r.url)
                if canon in seen_urls:
                    continue
                if "linkedin.com" not in canon.lower():
                    continue

                parsed = urlparse(canon)
                path = parsed.path.strip("/")
                # Filter utility / authwall paths
                if any(path.startswith(x) for x in ("checkpoint", "login", "signup", "legal", "jobs", "directory")):
                    continue

                seen_urls.add(canon)
                item_type = self._detect_item_type(canon)
                username = self._extract_username(canon)
                clean_t = self._clean_title(r.title, canon)

                items.append(DiscoveredItem(
                    title=clean_t,
                    url=canon,
                    description=r.snippet,
                    source_type="LINKEDIN",
                    raw_metadata={
                        "query": q,
                        "snippet": r.snippet,
                        "platform": "linkedin",
                        "post_type": item_type,
                        "username": username
                    }
                ))
        return items
