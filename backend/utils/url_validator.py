import re
from urllib.parse import urlparse, parse_qs, urlunparse
from typing import Optional, Tuple

def ensure_url_scheme(url: str, default_scheme: str = "https") -> str:
    """Ensures an input URL begins with an http or https protocol scheme."""
    if not url:
        return ""
    clean = url.strip()
    if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*://', clean):
        return f"{default_scheme}://{clean}"
    return clean

def validate_url(url: str) -> bool:
    """Checks whether the string is a well-formed http or https URL."""
    try:
        url = ensure_url_scheme(url)
        parsed = urlparse(url)
        return bool(parsed.scheme in ("http", "https") and parsed.netloc)
    except Exception:
        return False

def canonicalize_url(url: str) -> str:
    """Strips tracking query params (utm_*, ref, etc.) and normalizes URLs."""
    try:
        url = ensure_url_scheme(url)
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
    url = ensure_url_scheme(url)
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

