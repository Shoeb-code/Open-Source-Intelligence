from typing import List
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.discovery.search_providers import SearchProviderFactory
from backend.utils.url_validator import canonicalize_url


class WebpageCollector:
    """Discovers conference pages, webinars, blogs, and guest talks."""

    def __init__(self):
        self.search_provider = SearchProviderFactory.get_provider()

    def discover(self, queries: List[str], max_per_query: int = 5) -> List[DiscoveredItem]:
        items: List[DiscoveredItem] = []
        seen_urls = set()

        for q in queries:
            results = self.search_provider.search(q, limit=max_per_query, source_type="EVENT")
            for r in results:
                canon = canonicalize_url(r.url)
                if canon not in seen_urls:
                    seen_urls.add(canon)
                    items.append(DiscoveredItem(
                        title=r.title,
                        url=canon,
                        description=r.snippet,
                        source_type="EVENT",
                        raw_metadata={"query": q, "snippet": r.snippet}
                    ))
        return items

