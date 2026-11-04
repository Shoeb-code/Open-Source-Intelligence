import re
from urllib.parse import urlparse, parse_qs, urlunparse
from typing import Optional, Tuple

def validate_url(url: str) -> bool:
    """Checks whether the string is a well-formed http or https URL."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except Exception:
        return False

def canonicalize_url(url: str) -> str:
    """Strips tracking query params (utm_*, ref, etc.) and normalizes URLs."""
    try:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        # Filter tracking parameters
        clean_query = {
            k: v for k, v in query.items()
            if not k.startswith("utm_") and k not in ("ref", "fbclid", "gclid", "source")
        }
        # Reconstruct query string
        pairs = []
        for k, vals in sorted(clean_query.items()):
            for v in vals:
                pairs.append(f"{k}={v}")
        new_query = "&".join(pairs)
        
        path = parsed.path.rstrip("/")
        if not path:
            path = ""
            
        return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", new_query, ""))
    except Exception:
        return url

def extract_youtube_video_id(url: str) -> Optional[str]:
    """Extracts YouTube 11-character video ID from varied URL formats."""
    patterns = [
        r'(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/live\/|\/shorts\/)([a-zA-Z0-9_-]{11})',
        r'watch\?.*v=([a-zA-Z0-9_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def detect_platform(url: str) -> str:
    """Detects whether a URL belongs to LinkedIn, YouTube, Instagram, or generic Web."""
    netloc = urlparse(url).netloc.lower()
    if "youtube.com" in netloc or "youtu.be" in netloc:
        return "youtube"
    elif "linkedin.com" in netloc:
        return "linkedin"
    elif "instagram.com" in netloc:
        return "instagram"
    elif "twitter.com" in netloc or "x.com" in netloc:
        return "twitter"
    return "web"

