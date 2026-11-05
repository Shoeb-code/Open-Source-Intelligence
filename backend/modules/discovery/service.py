from typing import List, Dict
from backend.modules.persons.schemas import IdentityContext
from backend.modules.discovery.query_builder import QueryBuilder
from backend.modules.collectors.youtube import YouTubeCollector, DiscoveredItem
from backend.modules.collectors.news import NewsCollector
from backend.modules.collectors.podcasts import PodcastCollector
from backend.modules.collectors.webpages import WebpageCollector
from backend.utils.logger import logger


class DiscoveryService:
    """Orchestrates multi-source public appearance discovery across YouTube, News, Podcasts, and Events."""

    def __init__(self):
        self.youtube_collector = YouTubeCollector()
        self.news_collector = NewsCollector()
        self.podcast_collector = PodcastCollector()
        self.webpage_collector = WebpageCollector()

    def run_discovery(self, context: IdentityContext) -> List[DiscoveredItem]:
        logger.info(f"Initiating discovery for identity: '{context.name}' ({context.person_id})")
        queries_by_type = QueryBuilder.build_queries(context)
        discovered_items: List[DiscoveredItem] = []

        # 1. YouTube discovery
        if "youtube" in queries_by_type:
            logger.info("Executing YouTube discovery...")
            yt_items = self.youtube_collector.discover(queries_by_type["youtube"], max_per_query=3)
            discovered_items.extend(yt_items)
            logger.info(f"YouTube discovery found {len(yt_items)} candidate(s)")

        # 2. News discovery
        if "news" in queries_by_type:
            logger.info("Executing News discovery...")
            news_items = self.news_collector.discover(queries_by_type["news"], max_per_query=3)
            discovered_items.extend(news_items)
            logger.info(f"News discovery found {len(news_items)} candidate(s)")

        # 3. Podcast discovery
        if "podcasts" in queries_by_type:
            logger.info("Executing Podcast discovery...")
            pod_items = self.podcast_collector.discover(queries_by_type["podcasts"], max_per_query=3)
            discovered_items.extend(pod_items)
            logger.info(f"Podcast discovery found {len(pod_items)} candidate(s)")

        # 4. Events discovery
        if "events" in queries_by_type:
            logger.info("Executing Events & Conferences discovery...")
            event_items = self.webpage_collector.discover(queries_by_type["events"], max_per_query=3)
            discovered_items.extend(event_items)
            logger.info(f"Events discovery found {len(event_items)} candidate(s)")

        logger.info(f"Total candidate appearances discovered: {len(discovered_items)}")
        return discovered_items

