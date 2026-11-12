import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from backend.config import settings
from backend.utils.http_pool import borrow_http_client
from backend.utils.logger import logger
from backend.utils.url_validator import extract_youtube_video_id, canonicalize_url


class DiscoveredItem(BaseModel):
    title: str
    url: str
    publisher: Optional[str] = None
    description: Optional[str] = None
    published_at: Optional[datetime] = None
    source_type: str  # YOUTUBE, NEWS, PODCAST, EVENT, WEBPAGE
    raw_metadata: dict = {}


class YouTubeCollector:
    """Discovers YouTube public appearances (podcasts, interviews, talks) via API or yt-dlp."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.YOUTUBE_API_KEY

    def search_via_api(self, query: str, max_results: int = 5) -> List[DiscoveredItem]:
        items: List[DiscoveredItem] = []
        if not self.api_key:
            return items

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "key": self.api_key,
            "q": query,
            "part": "snippet",
            "type": "video",
            "maxResults": max_results
        }
        try:
            with borrow_http_client(timeout_seconds=10.0, connect_timeout=4.0) as client:
                res = client.get(url, params=params)
                res.raise_for_status()
                data = res.json()
                for v in data.get("items", []):
                    vid_id = v.get("id", {}).get("videoId")
                    if not vid_id:
                        continue
                    snippet = v.get("snippet", {})
                    pub_str = snippet.get("publishedAt")
                    pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00")) if pub_str else None
                    items.append(DiscoveredItem(
                        title=snippet.get("title", ""),
                        url=f"https://www.youtube.com/watch?v={vid_id}",
                        publisher=snippet.get("channelTitle"),
                        description=snippet.get("description"),
                        published_at=pub_dt,
                        source_type="YOUTUBE",
                        raw_metadata={"videoId": vid_id, "channelId": snippet.get("channelId")}
                    ))
        except Exception as e:
            logger.warning(f"YouTube Data API query failed for '{query}': {e}")
        return items

    def search_via_ytdlp(self, query: str, max_results: int = 5) -> List[DiscoveredItem]:
        """Fallback search using yt-dlp flat-playlist metadata."""
        items: List[DiscoveredItem] = []
        try:
            ytdlp_bin = shutil.which("yt-dlp")
            cmd = [ytdlp_bin] if ytdlp_bin else [sys.executable, "-m", "yt_dlp"]
            cmd.extend([
                f"ytsearch{max_results}:{query}",
                "--dump-json",
                "--flat-playlist",
                "--skip-download",
                "--socket-timeout", "5",
                "--no-warnings"
            ])
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=12,
                check=False
            )
            if result.returncode == 0 and result.stdout:
                for line in result.stdout.strip().split("\n"):
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        vid_id = data.get("id") or extract_youtube_video_id(data.get("url", ""))
                        if not vid_id:
                            continue
                        url = f"https://www.youtube.com/watch?v={vid_id}"
                        items.append(DiscoveredItem(
                            title=data.get("title") or "YouTube Video",
                            url=url,
                            publisher=data.get("uploader") or data.get("channel"),
                            description=data.get("description"),
                            source_type="YOUTUBE",
                            raw_metadata=data
                        ))
                    except Exception:
                        continue
        except Exception as e:
            logger.warning(f"yt-dlp discovery failed for '{query}': {e}")
        return items

    def _discover_single_query(self, query: str, max_per_query: int) -> List[DiscoveredItem]:
        results = []
        if self.api_key:
            results = self.search_via_api(query, max_results=max_per_query)
        if not results:
            results = self.search_via_ytdlp(query, max_results=max_per_query)
        return results

    def discover(self, queries: List[str], max_per_query: int = 4) -> List[DiscoveredItem]:
        all_items: List[DiscoveredItem] = []
        seen_urls = set()
        if not queries:
            return all_items

        max_workers = max(
            1,
            min(
                len(queries),
                settings.QUERY_MAX_WORKERS if self.api_key else min(4, settings.QUERY_MAX_WORKERS),
            ),
        )
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._discover_single_query, q, max_per_query) for q in queries]
            for fut in futures:
                for item in fut.result():
                    canon = canonicalize_url(item.url)
                    if canon not in seen_urls:
                        seen_urls.add(canon)
                        all_items.append(item)

        return all_items

