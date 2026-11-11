import re
from typing import List, Optional
from urllib.parse import urlparse
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.discovery.search_providers import SearchProviderFactory
from backend.utils.url_validator import canonicalize_url


class InstagramCollector:
    """Discovers public Instagram profiles, posts, reels, and video keynote appearances."""

    def __init__(self):
        self.search_provider = SearchProviderFactory.get_provider()

    @staticmethod
    def _extract_username(url: str) -> Optional[str]:
        try:
            parsed = urlparse(url)
            path = parsed.path.strip("/")
            if not path:
                return None
            parts = path.split("/")
            if parts[0] in ("p", "reel", "tv", "stories") and len(parts) > 1:
                return None
            if parts[0] not in ("explore", "accounts", "legal", "developer", "about", "directory"):
                return parts[0]
            return None
        except Exception:
            return None

    @staticmethod
    def _detect_item_type(url: str) -> str:
        url_lower = url.lower()
        if "/reel/" in url_lower:
            return "INSTAGRAM_REEL"
        elif "/p/" in url_lower:
            return "INSTAGRAM_POST"
        elif "/tv/" in url_lower:
            return "INSTAGRAM_VIDEO"
        return "INSTAGRAM_PROFILE"

    @staticmethod
    def _clean_title(title: str, url: str) -> str:
        if not title:
            return "Instagram Appearance"
        clean = title
        clean = re.sub(r'•\s*Instagram(?:\s+photos\s+and\s+videos)?', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s*-\s*Instagram\s*$', '', clean, flags=re.IGNORECASE)
        clean = clean.strip().rstrip("-|• ")
        if not clean:
            parsed_user = InstagramCollector._extract_username(url)
            return f"Instagram Profile (@{parsed_user})" if parsed_user else "Instagram Appearance"
        return clean

    def discover(self, queries: List[str], max_per_query: int = 4) -> List[DiscoveredItem]:
        items: List[DiscoveredItem] = []
        seen_urls = set()

        for q, results in self.search_provider.search_batch(queries, limit=max_per_query, source_type="INSTAGRAM"):
            for r in results:
                canon = canonicalize_url(r.url)
                if canon in seen_urls:
                    continue
                if "instagram.com" not in canon.lower():
                    continue

                # Filter out system and utility pages
                parsed = urlparse(canon)
                path = parsed.path.strip("/")
                if any(path.startswith(x) for x in ("accounts", "explore", "legal", "about", "developer", "directory")):
                    continue

                seen_urls.add(canon)
                item_type = self._detect_item_type(canon)
                username = self._extract_username(canon)
                clean_t = self._clean_title(r.title, canon)

                items.append(DiscoveredItem(
                    title=clean_t,
                    url=canon,
                    description=r.snippet,
                    source_type="INSTAGRAM",
                    raw_metadata={
                        "query": q,
                        "snippet": r.snippet,
                        "platform": "instagram",
                        "post_type": item_type,
                        "username": username
                    }
                ))
        return items

