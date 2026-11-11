from typing import List
from backend.modules.collectors.youtube import DiscoveredItem
from backend.modules.discovery.search_providers import SearchProviderFactory
from backend.utils.url_validator import canonicalize_url


class PodcastCollector:
    """Discovers external podcast episodes and interview transcripts."""

    def __init__(self):
        self.search_provider = SearchProviderFactory.get_provider()

    def discover(self, queries: List[str], max_per_query: int = 5) -> List[DiscoveredItem]:
        items: List[DiscoveredItem] = []
        seen_urls = set()

        for q, results in self.search_provider.search_batch(queries, limit=max_per_query, source_type="PODCAST"):
            for r in results:
                canon = canonicalize_url(r.url)
                if canon not in seen_urls:
                    seen_urls.add(canon)
                    items.append(DiscoveredItem(
                        title=r.title,
                        url=canon,
                        description=r.snippet,
                        source_type="PODCAST",
                        raw_metadata={"query": q, "snippet": r.snippet}
                    ))
        return items

