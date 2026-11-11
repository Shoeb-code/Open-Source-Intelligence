import json
import re
import threading
import time
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse, urlunparse
import httpx
from backend.config import settings
from backend.utils.http_pool import borrow_http_client
from backend.utils.logger import logger
from backend.utils.text_cleaner import clean_text

_last_extraction_method_var: ContextVar[Optional[str]] = ContextVar(
    "article_last_extraction_method",
    default=None,
)
_last_extraction_details_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "article_last_extraction_details",
    default=None,
)

# Process-wide Firecrawl semaphore shared by all ArticleExtractor callers
_firecrawl_sem_lock = threading.Lock()
_firecrawl_sem: Optional[threading.Semaphore] = None
_firecrawl_sem_limit: Optional[int] = None

# Phrases that strongly indicate bot-protection, CAPTCHA, login gates, or access blocks
_STRONG_BLOCK_PHRASES = (
    "verify you are human",
    "verify that you are human",
    "are you a robot",
    "i am not a robot",
    "human verification",
    "checking your browser before accessing",
    "checking if the site connection is secure",
    "enable javascript and cookies to continue",
    "please enable cookies and reload",
    "please complete the captcha",
    "complete the security check",
    "solve the captcha",
    "attention required! | cloudflare",
    "you have been blocked",
    "sorry, you have been blocked",
    "request was blocked",
    "unusual traffic from your computer",
    "automated queries from your",
    "sign in to view",
    "sign in to continue",
    "log in to continue",
    "login to continue",
    "join linkedin to view",
    "sign in or join now",
    "create a free account to continue",
    "subscribe to continue reading",
    "enable javascript to run this app",
    "this content isn't available right now",
)

_BLOCK_TITLE_KEYWORDS = (
    "just a moment",
    "attention required",
    "access denied",
    "403 forbidden",
    "401 unauthorized",
    "robot check",
    "security check",
    "human verification",
    "verify your identity",
    "verify you are human",
    "sign in",
    "log in",
    "login",
)

_MODERATE_BLOCK_KEYWORDS = (
    "captcha",
    "recaptcha",
    "hcaptcha",
    "turnstile",
    "cloudflare",
    "access denied",
    "forbidden",
    "unauthorized",
    "login required",
    "please log in",
    "please sign in",
)

_COOKIE_BOILERPLATE_PHRASES = (
    "we use cookies",
    "accept all cookies",
    "accept cookies",
    "cookie preferences",
    "cookie settings",
    "manage cookies",
    "reject all cookies",
    "by clicking accept",
)

_CAPTCHA_MARKERS = re.compile(
    r"g-recaptcha|h-captcha|cf-turnstile|challenges\.cloudflare\.com|"
    r"/cdn-cgi/challenge-platform|captcha-delivery|px-captcha",
    re.IGNORECASE,
)

_BINARY_ASSET_EXTENSIONS = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".mp3",
    ".mp4",
    ".zip",
    ".exe",
    ".pdf",
)

_LINKEDIN_MIN_CONTENT_LENGTH = 25
_LINKEDIN_MIN_ALPHA_WORDS = 4
_LINKEDIN_BOILERPLATE_PHRASES = (
    "sign in or join linkedin",
    "join linkedin to view",
    "sign in to view",
    "authwall",
    "request denied",
    "linkedin is the world's largest",
    "largest business network",
    "world's largest professional community",
    "world’s largest professional community",
)

_RETRYABLE_STATUS_CODES = (429, 502, 503)


def _redact_api_key(text: str) -> str:
    for secret in (settings.FIRECRAWL_API_KEY, settings.EXA_API_KEY):
        if secret and secret in text:
            text = text.replace(secret, "[REDACTED]")
    return text


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _FirecrawlScrapeResult:
    success: bool
    markdown: Optional[str] = None
    title: Optional[str] = None
    publisher: Optional[str] = None
    source_url: Optional[str] = None
    target_status_code: Optional[int] = None
    api_status_code: Optional[int] = None
    error_reason: Optional[str] = None
    is_restricted: bool = False


class ArticleExtractor:
    """Extracts readable website, blog, news, podcast, event, and LinkedIn content via Firecrawl /v2/scrape."""

    @staticmethod
    def get_last_extraction_method() -> Optional[str]:
        """Returns the extraction method ('firecrawl', 'exa_contents', or 'failed') for the current execution context."""
        return _last_extraction_method_var.get()

    @staticmethod
    def get_last_extraction_details() -> Optional[Dict[str, Any]]:
        """Returns structured extraction provenance metadata for the current execution context."""
        return _last_extraction_details_var.get()

    @classmethod
    def _get_firecrawl_semaphore(cls) -> threading.Semaphore:
        limit = max(1, int(settings.FIRECRAWL_MAX_CONCURRENCY or 4))
        with _firecrawl_sem_lock:
            global _firecrawl_sem, _firecrawl_sem_limit
            if _firecrawl_sem is None or _firecrawl_sem_limit != limit:
                _firecrawl_sem = threading.Semaphore(limit)
                _firecrawl_sem_limit = limit
            return _firecrawl_sem

    @staticmethod
    def _is_binary_asset_url(url: str) -> Optional[str]:
        try:
            path = (urlparse(url).path or "").lower()
        except Exception:
            return None
        for ext in _BINARY_ASSET_EXTENSIONS:
            if path.endswith(ext):
                return ext
        return None

    @staticmethod
    def _is_linkedin_url(url: str) -> bool:
        host = (urlparse(url).netloc or "").lower()
        return host == "linkedin.com" or host.endswith(".linkedin.com")

    @staticmethod
    def _normalize_fetch_url(url: str) -> str:
        """Upgrades bare linkedin.com host to www.linkedin.com cleanly before provider calls."""
        try:
            parsed = urlparse(url)
            if parsed.netloc.lower() == "linkedin.com":
                return urlunparse(parsed._replace(netloc="www.linkedin.com"))
        except Exception:
            pass
        return url

    @staticmethod
    def _clean_linkedin_title(title: Optional[str]) -> Optional[str]:
        if not title:
            return None
        cleaned = re.sub(r"\s*[|\-]\s*LinkedIn\s*$", "", title, flags=re.IGNORECASE).strip() or title
        lowered = cleaned.lower()
        if any(tok in lowered for tok in ("sign in", "log in", "login", "authwall")):
            return None
        return cleaned

    @staticmethod
    def _extract_jsonld_text(ld_data: Any) -> Tuple[Optional[str], Optional[str]]:
        """Extracts SocialMediaPosting/Article/Person text and title from structured JSON-LD metadata when available."""
        if not ld_data:
            return None, None
        nodes = []
        raw_items = ld_data if isinstance(ld_data, list) else [ld_data]
        for entry in raw_items:
            if isinstance(entry, str):
                try:
                    entry = json.loads(entry)
                except Exception:
                    continue
            if isinstance(entry, dict):
                if isinstance(entry.get("@graph"), list):
                    nodes.extend(n for n in entry["@graph"] if isinstance(n, dict))
                nodes.append(entry)

        best_body = ""
        resolved_title = None
        for node in nodes:
            raw_type = node.get("@type")
            types = raw_type if isinstance(raw_type, list) else [raw_type]
            if any(t in ("SocialMediaPosting", "DiscussionForumPosting", "Article", "NewsArticle", "BlogPosting") for t in types):
                candidate = clean_text(
                    str(
                        node.get("articleBody")
                        or node.get("text")
                        or node.get("description")
                        or node.get("headline")
                        or ""
                    )
                )
                if len(candidate) > len(best_body):
                    best_body = candidate
                headline = clean_text(str(node.get("headline") or ""))
                if headline and not resolved_title:
                    resolved_title = headline
            elif "Person" in types and not best_body:
                parts = []
                if node.get("name") and not resolved_title:
                    resolved_title = clean_text(str(node["name"]))
                if node.get("jobTitle"):
                    jt = node["jobTitle"]
                    parts.append(f"Role: {', '.join(jt) if isinstance(jt, list) else clean_text(str(jt))}")
                if node.get("description"):
                    parts.append(clean_text(str(node["description"])))
                best_body = clean_text("\n".join(p for p in parts if p))

        return (best_body or None), resolved_title

    @staticmethod
    def _extract_retry_after_seconds(headers: Any) -> Optional[float]:
        if not headers:
            return None
        raw = None
        for key in ("Retry-After", "retry-after"):
            try:
                val = headers.get(key)
                if val is not None:
                    raw = val
                    break
            except Exception:
                pass
        if raw is None:
            return None
        try:
            seconds = float(str(raw).strip())
            if seconds < 0:
                return 0.0
            return min(seconds, 5.0)
        except ValueError:
            return None

    @staticmethod
    def _detect_wall_reason(
        text: str,
        raw_gate_text: str,
        page_title: Optional[str],
        has_password_form: bool,
        has_captcha_widget: bool,
        substantive_p_count: int,
    ) -> Optional[str]:
        lowered = text.lower()
        combined_preview = f"{lowered[:800]} {raw_gate_text[:1000]}".lower()

        if page_title:
            title_lower = page_title.lower()
            if len(text) < 1500 and any(tok in title_lower for tok in _BLOCK_TITLE_KEYWORDS):
                return "blocked_title"

        if has_captcha_widget and len(text) < 2500:
            return "captcha_widget"

        if has_password_form and (substantive_p_count < 3 or len(text) < 1200):
            return "login_form"

        if len(text) < 2500:
            if any(phrase in combined_preview for phrase in _STRONG_BLOCK_PHRASES):
                return "bot_or_login_wall"
        elif any(phrase in lowered[:500] for phrase in _STRONG_BLOCK_PHRASES):
            return "bot_or_login_wall"

        if len(text) < 1000 or (substantive_p_count < 2 and len(text) < 1500):
            if any(kw in combined_preview for kw in _MODERATE_BLOCK_KEYWORDS):
                return "restricted_gate_text"

        return None

    @classmethod
    def _assess_content_quality(
        cls,
        cleaned_text: str,
        min_content_length: int,
        page_title: Optional[str],
        raw_gate_text: str,
        has_password_form: bool,
        has_captcha_widget: bool,
        used_body_fallback: bool,
        link_ratio: float,
        substantive_p_count: int,
    ) -> Tuple[bool, Optional[str]]:
        if not cleaned_text:
            wall_reason = cls._detect_wall_reason(
                "",
                raw_gate_text,
                page_title,
                has_password_form,
                has_captcha_widget,
                0,
            )
            return False, wall_reason or "empty_content"

        wall_reason = cls._detect_wall_reason(
            cleaned_text,
            raw_gate_text,
            page_title,
            has_password_form,
            has_captcha_widget,
            substantive_p_count,
        )
        if wall_reason:
            return False, wall_reason

        lowered = cleaned_text.lower()
        cookie_hits = sum(1 for phrase in _COOKIE_BOILERPLATE_PHRASES if phrase in lowered)
        if cookie_hits >= 2 and len(cleaned_text) < 1200:
            return False, "cookie_banner_boilerplate"
        if cookie_hits >= 1 and (len(cleaned_text) < 600 or substantive_p_count < 2):
            return False, "cookie_banner_boilerplate"

        if used_body_fallback and link_ratio >= 0.75 and substantive_p_count < 2:
            return False, "navigation_boilerplate"

        if len(cleaned_text) < min_content_length:
            return False, f"too_short ({len(cleaned_text)} < {min_content_length} chars)"

        alpha_words = re.findall(r"[A-Za-z]{2,}", cleaned_text)
        min_words = max(5, min(20, min_content_length // 10))
        if len(alpha_words) < min_words:
            return False, f"insufficient_words ({len(alpha_words)} < {min_words})"

        return True, None

    @classmethod
    def _validate_markdown_content(
        cls,
        raw_text: Optional[str],
        page_title: Optional[str],
        min_content_length: int,
        is_linkedin: bool = False,
        target_status_code: Optional[int] = None,
    ) -> Tuple[Optional[str], bool, Optional[str], bool]:
        """
        Validates Firecrawl/Exa content for quality, length, and block/challenge gates.
        Returns (cleaned_text, is_valid, reject_reason, is_restricted).
        """
        if target_status_code in (404, 410):
            return None, False, f"target_http_{target_status_code}", False

        cleaned = clean_text(raw_text) if raw_text else ""
        if not cleaned:
            restricted_code = target_status_code in (401, 403, 429, 999)
            return None, False, "empty_content", restricted_code

        paragraphs = [
            p.strip()
            for p in re.split(r"\n{2,}", cleaned)
            if len(re.sub(r"[#>*`\[\]()_-]+", "", p).strip()) >= 40
        ]
        substantive_p_count = len(paragraphs)
        link_labels = re.findall(r"\[([^\]]+)\]\([^)]+\)", cleaned)
        link_ratio = sum(len(lbl) for lbl in link_labels) / max(len(cleaned), 1)
        has_captcha = bool(_CAPTCHA_MARKERS.search(cleaned))
        has_password_prompt = any(
            tok in cleaned.lower()[:1200]
            for tok in ("enter your password", "session_password", "type=\"password\"")
        )

        if is_linkedin:
            lowered = cleaned.lower()
            if any(phrase in lowered for phrase in _LINKEDIN_BOILERPLATE_PHRASES):
                return None, False, "bot_or_login_wall", True

            wall = cls._detect_wall_reason(
                cleaned,
                cleaned[:1500],
                page_title,
                has_password_prompt,
                has_captcha,
                max(substantive_p_count, 2),
            )
            if wall:
                return None, False, wall, True

            if target_status_code in (401, 403, 429, 999):
                return None, False, f"target_http_{target_status_code}", True

            if len(cleaned) < _LINKEDIN_MIN_CONTENT_LENGTH:
                return None, False, f"too_short ({len(cleaned)} < {_LINKEDIN_MIN_CONTENT_LENGTH} chars)", False

            alpha_words = re.findall(r"[A-Za-z]{2,}", cleaned)
            if len(alpha_words) < _LINKEDIN_MIN_ALPHA_WORDS:
                return None, False, f"insufficient_words ({len(alpha_words)} < {_LINKEDIN_MIN_ALPHA_WORDS})", False

            return cleaned, True, None, False

        is_valid, reason = cls._assess_content_quality(
            cleaned_text=cleaned,
            min_content_length=min_content_length,
            page_title=page_title,
            raw_gate_text=cleaned[:1500],
            has_password_form=has_password_prompt,
            has_captcha_widget=has_captcha,
            used_body_fallback=substantive_p_count < 2,
            link_ratio=link_ratio,
            substantive_p_count=substantive_p_count,
        )
        if not is_valid:
            is_wall = reason in (
                "blocked_title",
                "captcha_widget",
                "login_form",
                "bot_or_login_wall",
                "restricted_gate_text",
            ) or (target_status_code in (401, 403, 429, 999))
            return None, False, reason, is_wall

        if target_status_code in (401, 403, 429, 999) and len(cleaned) < max(min_content_length * 2, 400):
            return None, False, f"target_http_{target_status_code}", True

        return cleaned, True, None, False

    @classmethod
    def _scrape_with_firecrawl(cls, url: str) -> _FirecrawlScrapeResult:
        """
        Calls Firecrawl /v2/scrape using the shared concurrency semaphore and bounded retries.
        Never exposes FIRECRAWL_API_KEY in logs or returned error reasons.
        """
        if not settings.FIRECRAWL_API_KEY:
            return _FirecrawlScrapeResult(
                success=False,
                error_reason="FIRECRAWL_API_KEY unset",
            )

        headers = {
            "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": bool(settings.FIRECRAWL_ONLY_MAIN_CONTENT),
        }
        scrape_url = settings.FIRECRAWL_SCRAPE_URL or "https://api.firecrawl.dev/v2/scrape"
        timeout_s = float(settings.FIRECRAWL_TIMEOUT_SECONDS or 20.0)
        connect_s = float(settings.FIRECRAWL_CONNECT_TIMEOUT_SECONDS or 5.0)
        max_retries = 2

        sem = cls._get_firecrawl_semaphore()
        last_error: Optional[str] = None
        last_status: Optional[int] = None
        last_restricted = False

        for attempt in range(max_retries + 1):
            retry_delay: Optional[float] = None
            sem.acquire()
            try:
                with borrow_http_client(
                    timeout_seconds=timeout_s,
                    connect_timeout=connect_s,
                    follow_redirects=False,
                ) as client:
                    res = client.post(scrape_url, headers=headers, json=payload)

                last_status = res.status_code
                if res.status_code == 200:
                    try:
                        body = res.json()
                    except Exception:
                        return _FirecrawlScrapeResult(
                            success=False,
                            api_status_code=200,
                            error_reason="Invalid JSON response from Firecrawl v2",
                        )

                    if not isinstance(body, dict):
                        return _FirecrawlScrapeResult(
                            success=False,
                            api_status_code=200,
                            error_reason="Malformed response payload from Firecrawl v2",
                        )

                    if body.get("success") is False:
                        err_msg = _redact_api_key(str(body.get("error") or "Firecrawl returned success=false"))
                        return _FirecrawlScrapeResult(
                            success=False,
                            api_status_code=200,
                            error_reason=err_msg,
                        )

                    data = body.get("data") if isinstance(body.get("data"), dict) else body
                    meta = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}

                    title = clean_text(
                        str(meta.get("title") or meta.get("ogTitle") or meta.get("og:title") or "")
                    ) or None
                    publisher = clean_text(
                        str(
                            meta.get("ogSiteName")
                            or meta.get("og:site_name")
                            or meta.get("siteName")
                            or meta.get("site_name")
                            or meta.get("publisher")
                            or ""
                        )
                    ) or None
                    source_url = str(meta.get("sourceURL") or meta.get("source_url") or meta.get("url") or url)
                    raw_target_status = meta.get("statusCode")
                    target_status = raw_target_status if isinstance(raw_target_status, int) else None

                    markdown = data.get("markdown") or data.get("content")
                    if not markdown and meta.get("jsonLd"):
                        ld_text, ld_title = cls._extract_jsonld_text(meta.get("jsonLd"))
                        markdown = ld_text
                        if not title and ld_title:
                            title = ld_title

                    return _FirecrawlScrapeResult(
                        success=True,
                        markdown=str(markdown) if markdown else None,
                        title=title,
                        publisher=publisher,
                        source_url=source_url,
                        target_status_code=target_status,
                        api_status_code=200,
                    )

                if res.status_code == 402:
                    return _FirecrawlScrapeResult(
                        success=False,
                        api_status_code=402,
                        error_reason="HTTP 402 - Credits unavailable",
                    )

                if res.status_code in _RETRYABLE_STATUS_CODES and attempt < max_retries:
                    retry_after = cls._extract_retry_after_seconds(getattr(res, "headers", None))
                    retry_delay = retry_after if retry_after is not None else min(0.4 * (2 ** attempt), 2.0)
                    last_error = f"HTTP {res.status_code}"
                    logger.warning(
                        f"[EXTRACTION] URL: {url} | [PROVIDER] Firecrawl v2 | Retry {attempt + 1}/{max_retries} after {last_error}"
                    )
                else:
                    last_restricted = res.status_code in (401, 403, 429)
                    last_error = f"HTTP {res.status_code}"
                    return _FirecrawlScrapeResult(
                        success=False,
                        api_status_code=res.status_code,
                        error_reason=last_error,
                        is_restricted=last_restricted,
                    )
            except httpx.TimeoutException as e:
                last_error = _redact_api_key(f"TimeoutException: {e}")
                if attempt == 0:
                    retry_delay = 0.25
                    logger.warning(
                        f"[EXTRACTION] URL: {url} | [PROVIDER] Firecrawl v2 | Retry 1/1 after API timeout"
                    )
                else:
                    return _FirecrawlScrapeResult(
                        success=False,
                        api_status_code=last_status,
                        error_reason=last_error,
                    )
            except httpx.HTTPError as e:
                last_error = _redact_api_key(f"{type(e).__name__}: {e}")
                if attempt == 0 and isinstance(e, httpx.TransportError) and not isinstance(e, httpx.ConnectError):
                    retry_delay = 0.25
                else:
                    return _FirecrawlScrapeResult(
                        success=False,
                        api_status_code=last_status,
                        error_reason=last_error,
                    )
            except Exception as e:
                last_error = _redact_api_key(f"{type(e).__name__}: {e}")
                return _FirecrawlScrapeResult(
                    success=False,
                    api_status_code=last_status,
                    error_reason=last_error,
                )
            finally:
                sem.release()

            if retry_delay is not None and retry_delay > 0:
                time.sleep(retry_delay)

        return _FirecrawlScrapeResult(
            success=False,
            api_status_code=last_status,
            error_reason=last_error or "Firecrawl scrape retries exhausted",
            is_restricted=last_restricted,
        )

    @classmethod
    def extract_with_firecrawl(cls, url: str) -> Optional[str]:
        """Scrapes an article/webpage using Firecrawl /v2/scrape and returns extracted Markdown text."""
        result = cls._scrape_with_firecrawl(url)
        return result.markdown if result.success else None

    @staticmethod
    def extract_with_exa_contents(url: str) -> Optional[Tuple[str, Optional[str]]]:
        """Fetches cached/indexed content for blocked LinkedIn URLs using Exa /contents without exposing EXA_API_KEY."""
        if not settings.EXA_API_KEY:
            return None
        try:
            headers = {
                "x-api-key": settings.EXA_API_KEY,
                "Content-Type": "application/json",
            }
            with borrow_http_client(timeout_seconds=10.0, connect_timeout=4.0, follow_redirects=False) as client:
                res = client.post(
                    "https://api.exa.ai/contents",
                    headers=headers,
                    json={"ids": [url], "text": {"maxCharacters": 4000}},
                )
                if res.status_code == 200:
                    results = res.json().get("results") or []
                    if results and isinstance(results[0], dict):
                        item = results[0]
                        raw_text = item.get("text") or " ".join(item.get("highlights") or [])
                        cleaned = clean_text(raw_text)
                        if cleaned and len(cleaned) >= _LINKEDIN_MIN_CONTENT_LENGTH:
                            title = clean_text(item.get("title") or "") or None
                            return cleaned, title
                else:
                    logger.warning(f"Exa /contents returned HTTP {res.status_code} for {url}")
        except Exception as e:
            safe_err = _redact_api_key(str(e))
            logger.warning(f"Exa /contents failed for {url} ({type(e).__name__}): {safe_err}")
        return None

    @staticmethod
    def _classify_quality(content_length: int) -> str:
        if content_length >= 800:
            return "HIGH"
        if content_length >= 200:
            return "MEDIUM"
        return "LOW"

    @classmethod
    def _record_provenance(
        cls,
        *,
        url: str,
        method: str,
        provider: str,
        status: str,
        api_status_code: Optional[int] = None,
        target_status_code: Optional[int] = None,
        page_title: Optional[str] = None,
        publisher: Optional[str] = None,
        content_length: int = 0,
        failure_reason: Optional[str] = None,
        error_details: Optional[str] = None,
        exa_fallback_note: Optional[str] = None,
    ) -> None:
        quality = cls._classify_quality(content_length) if status == "SUCCESS" else "NONE"
        details = {
            "source_url": url,
            "method": method,
            "provider": provider,
            "status": status,
            "api_status_code": api_status_code,
            "target_status_code": target_status_code,
            "page_title": page_title,
            "publisher": publisher,
            "content_length": content_length,
            "quality": quality,
            "retrieved_at": _utc_iso(),
            "failure_reason": failure_reason,
            "error_details": _redact_api_key(error_details) if error_details else None,
        }
        _last_extraction_method_var.set(method)
        _last_extraction_details_var.set(details)

        if status == "SUCCESS":
            logger.info(
                f"[EXTRACTION] URL: {url} | [PROVIDER] {provider} | [STATUS] SUCCESS | "
                f"[METHOD] {method} | [CONTENT_LENGTH] {content_length} | [QUALITY] {quality} | "
                f"[TITLE] {page_title or 'N/A'} | [PUBLISHER] {publisher or 'N/A'}"
            )
        else:
            safe_err = _redact_api_key(error_details or failure_reason or "Extraction failed")
            fallback_suffix = f" | [EXA_FALLBACK] {exa_fallback_note}" if exa_fallback_note else ""
            logger.warning(
                f"[EXTRACTION] URL: {url} | [PROVIDER] {provider} | [STATUS] {status} | "
                f"[ERROR] {safe_err}{fallback_suffix}"
            )

    @classmethod
    def extract_article_text(cls, url: str) -> Tuple[Optional[str], str]:
        """
        Returns (content_text, extraction_status).
        Status is SUCCESS, RESTRICTED, or FAILED.
        """
        text, status, _, _ = cls.extract_article(url)
        return text, status

    @classmethod
    def extract_article_with_method(
        cls,
        url: str,
        min_content_length: Optional[int] = None,
    ) -> Tuple[Optional[str], str, Optional[str], Optional[str], str]:
        """Returns (content_text, extraction_status, page_title, publisher, extraction_method)."""
        text, status, page_title, publisher = cls.extract_article(
            url,
            min_content_length=min_content_length,
        )
        method = _last_extraction_method_var.get() or ("firecrawl" if status == "SUCCESS" else "failed")
        return text, status, page_title, publisher, method

    @classmethod
    def extract_article(
        cls,
        url: str,
        min_content_length: Optional[int] = None,
    ) -> Tuple[Optional[str], str, Optional[str], Optional[str]]:
        """
        Extracts webpage/article/LinkedIn content directly via Firecrawl /v2/scrape (never direct HTTPX GET).
        LinkedIn falls back to Exa /contents when Firecrawl fails or returns blocked/insufficient content.
        Returns (content_text, extraction_status, page_title, publisher).
        """
        min_len = min_content_length if min_content_length is not None else settings.ARTICLE_MIN_CONTENT_LENGTH
        is_linkedin = cls._is_linkedin_url(url)

        binary_ext = cls._is_binary_asset_url(url)
        if binary_ext:
            cls._record_provenance(
                url=url,
                method="failed",
                provider="Firecrawl v2",
                status="FAILED",
                failure_reason=f"binary_asset:{binary_ext}",
                error_details=f"Skipped binary asset extension {binary_ext}",
            )
            return None, "FAILED", None, None

        fetch_url = cls._normalize_fetch_url(url) if is_linkedin else url
        fc = cls._scrape_with_firecrawl(fetch_url)

        fc_reject_reason: Optional[str] = None
        fc_is_restricted = fc.is_restricted
        safe_title = cls._clean_linkedin_title(fc.title) if is_linkedin else fc.title
        final_publisher = fc.publisher or ("LinkedIn" if is_linkedin else None)

        if fc.success:
            cleaned, is_valid, reject_reason, wall_restricted = cls._validate_markdown_content(
                fc.markdown,
                page_title=fc.title,
                min_content_length=min_len,
                is_linkedin=is_linkedin,
                target_status_code=fc.target_status_code,
            )
            if is_valid and cleaned:
                cls._record_provenance(
                    url=fc.source_url or url,
                    method="firecrawl",
                    provider="Firecrawl v2",
                    status="SUCCESS",
                    api_status_code=fc.api_status_code,
                    target_status_code=fc.target_status_code,
                    page_title=safe_title,
                    publisher=final_publisher,
                    content_length=len(cleaned),
                )
                return cleaned, "SUCCESS", safe_title, final_publisher

            fc_reject_reason = reject_reason
            fc_is_restricted = fc_is_restricted or wall_restricted
            if fc_is_restricted:
                safe_title = None
        else:
            fc_reject_reason = fc.error_reason

        # LinkedIn fallback to Exa /contents if Firecrawl failed or returned gated/insufficient text
        exa_fallback_note: Optional[str] = None
        if is_linkedin:
            if settings.EXA_API_KEY:
                exa_res = cls.extract_with_exa_contents(fetch_url)
                if not exa_res and fetch_url != url:
                    exa_res = cls.extract_with_exa_contents(url)
                if exa_res:
                    exa_raw_text, exa_title = exa_res
                    exa_clean_title = cls._clean_linkedin_title(exa_title) or safe_title
                    exa_cleaned, exa_valid, exa_reject, _ = cls._validate_markdown_content(
                        exa_raw_text,
                        page_title=exa_title,
                        min_content_length=min_len,
                        is_linkedin=True,
                    )
                    if exa_valid and exa_cleaned:
                        cls._record_provenance(
                            url=url,
                            method="exa_contents",
                            provider="Exa /contents",
                            status="SUCCESS",
                            api_status_code=fc.api_status_code,
                            target_status_code=fc.target_status_code,
                            page_title=exa_clean_title,
                            publisher=final_publisher or "LinkedIn",
                            content_length=len(exa_cleaned),
                        )
                        return exa_cleaned, "SUCCESS", exa_clean_title, final_publisher or "LinkedIn"
                    exa_fallback_note = f"rejected ({exa_reject})"
                else:
                    exa_fallback_note = "empty/failed"
            else:
                exa_fallback_note = "EXA_API_KEY unset"

        final_status = "RESTRICTED" if fc_is_restricted else "FAILED"
        if final_status == "RESTRICTED":
            safe_title = None

        cls._record_provenance(
            url=url,
            method="failed",
            provider="Firecrawl v2",
            status=final_status,
            api_status_code=fc.api_status_code,
            target_status_code=fc.target_status_code,
            page_title=safe_title,
            publisher=final_publisher,
            failure_reason=fc_reject_reason or fc.error_reason,
            error_details=fc.error_reason or fc_reject_reason,
            exa_fallback_note=exa_fallback_note,
        )
        return None, final_status, safe_title, final_publisher
