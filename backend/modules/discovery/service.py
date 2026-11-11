from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Tuple
from backend.config import settings
from backend.modules.persons.schemas import IdentityContext
from backend.modules.discovery.query_builder import QueryBuilder
from backend.modules.collectors.youtube import YouTubeCollector, DiscoveredItem
from backend.modules.collectors.news import NewsCollector
from backend.modules.collectors.podcasts import PodcastCollector
from backend.modules.collectors.webpages import WebpageCollector
from backend.modules.collectors.linkedin import LinkedInCollector
from backend.modules.collectors.instagram import InstagramCollector
from backend.utils.logger import logger


class DiscoveryService:
    """Orchestrates concurrent multi-source public appearance discovery across YouTube, News, Podcasts, Events, LinkedIn, and Instagram."""

    def __init__(self):
        self.youtube_collector = YouTubeCollector()
        self.news_collector = NewsCollector()
        self.podcast_collector = PodcastCollector()
        self.webpage_collector = WebpageCollector()
        self.linkedin_collector = LinkedInCollector()
        self.instagram_collector = InstagramCollector()

    def run_discovery(self, context: IdentityContext) -> List[DiscoveredItem]:
        logger.info(f"Initiating discovery for identity: '{context.name}' ({context.person_id})")
        queries_by_type = QueryBuilder.build_queries(context)
        discovered_items: List[DiscoveredItem] = []

        tasks: List[Tuple[str, str, Callable[[List[str], int], List[DiscoveredItem]]]] = [
            ("youtube", "YouTube", self.youtube_collector.discover),
            ("news", "News", self.news_collector.discover),
            ("podcasts", "Podcast", self.podcast_collector.discover),
            ("events", "Events & Conferences", self.webpage_collector.discover),
            ("linkedin", "LinkedIn", self.linkedin_collector.discover),
            ("instagram", "Instagram", self.instagram_collector.discover),
        ]

        active_tasks = [(key, label, fn) for key, label, fn in tasks if key in queries_by_type]
        if not active_tasks:
            return discovered_items

        max_workers = max(1, min(len(active_tasks), settings.DISCOVERY_MAX_WORKERS))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                key: (label, executor.submit(fn, queries_by_type[key], 3))
                for key, label, fn in active_tasks
            }
            for key, label, _ in active_tasks:
                _, fut = futures[key]
                try:
                    items = fut.result()
                    discovered_items.extend(items)
                    logger.info(f"{label} discovery found {len(items)} candidate(s)")
                except Exception as e:
                    logger.warning(f"{label} discovery failed: {e}")

        logger.info(f"Total candidate appearances discovered: {len(discovered_items)}")
        return discovered_items
