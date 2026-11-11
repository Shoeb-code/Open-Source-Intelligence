import re
from contextvars import ContextVar
from typing import Optional, Tuple
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from backend.config import settings
from backend.utils.http_pool import borrow_http_client
from backend.utils.logger import logger
from backend.utils.text_cleaner import clean_text

_last_extraction_method_var: ContextVar[Optional[str]] = ContextVar(
    "article_last_extraction_method",
    default=None,
)

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

_NOISE_ATTR_PATTERN = re.compile(
    r"(?:^|[\s_-])(cookie|cookies|consent|gdpr|onetrust|cookiebot|navbar|nav-menu|breadcrumb|"
    r"site-header|site-footer|promo-banner|newsletter-popup|paywall)(?:$|[\s_-])",
    re.IGNORECASE,
)

_CAPTCHA_HTML_PATTERN = re.compile(
    r"g-recaptcha|h-captcha|cf-turnstile|challenges\.cloudflare\.com|"
    r"/cdn-cgi/challenge-platform|captcha-delivery|px-captcha",
    re.IGNORECASE,
)


_GATED_SOCIAL_HOSTS = ("linkedin.com", "instagram.com", "facebook.com")


def _redact_api_key(text: str) -> str:
    if settings.FIRECRAWL_API_KEY and settings.FIRECRAWL_API_KEY in text:
        return text.replace(settings.FIRECRAWL_API_KEY, "[REDACTED]")
    return text


class ArticleExtractor:
    """Extracts readable article or webpage content, prioritizing free HTTPX + BeautifulSoup before Firecrawl fallback."""

    @staticmethod
    def get_last_extraction_method() -> Optional[str]:
        """Returns the extraction method ('httpx', 'firecrawl', or 'failed') recorded in the current execution context."""
        return _last_extraction_method_var.get()

    @staticmethod
    def _extract_page_metadata(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
        page_title = None
        if soup.title and soup.title.string:
            page_title = clean_text(soup.title.string)
        og_title = soup.find("meta", property="og:title") or soup.find("meta", attrs={"name": "twitter:title"})
        if og_title and og_title.get("content"):
            page_title = clean_text(og_title["content"])

        publisher = None
        og_site = soup.find("meta", property="og:site_name") or soup.find("meta", attrs={"name": "publisher"})
        if og_site and og_site.get("content"):
            publisher = clean_text(og_site["content"])
        return page_title or None, publisher or None

    @staticmethod
    def _strip_noise_elements(soup: BeautifulSoup) -> None:
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "svg", "iframe", "form", "dialog"]):
            tag.decompose()

        for elem in list(soup.find_all(["div", "section", "ul"])):
            role = (elem.get("role") or "").lower()
            if role in ("navigation", "banner", "dialog"):
                elem.decompose()
                continue
            classes = " ".join(elem.get("class") or [])
            elem_id = elem.get("id") or ""
            if _NOISE_ATTR_PATTERN.search(f"{classes} {elem_id}"):
                elem.decompose()

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
    def _parse_and_validate_html(
        cls,
        html: str,
        min_content_length: int,
    ) -> Tuple[Optional[str], str, Optional[str], Optional[str], Optional[str]]:
        """Parses HTML with BeautifulSoup, validates article quality, and returns (text, status, title, publisher, reason)."""
        if not html or not html.strip():
            return None, "FAILED", None, None, "empty_html"

        soup = BeautifulSoup(html, "lxml")
        page_title, publisher = cls._extract_page_metadata(soup)

        # Capture gate/CAPTCHA/login signals before decomposing <form>/<dialog> elements
        has_password_form = bool(soup.find("input", attrs={"type": re.compile(r"^password$", re.IGNORECASE)}))
        has_captcha_widget = bool(_CAPTCHA_HTML_PATTERN.search(html))
        raw_gate_text = clean_text(soup.get_text(separator=" ", strip=True))[:1500]

        cls._strip_noise_elements(soup)

        article_elem = soup.find("article")
        main_tag = soup.find("main")
        main_elem = article_elem or main_tag or soup.find("body")
        used_body_fallback = article_elem is None and main_tag is None

        if not main_elem:
            wall = cls._detect_wall_reason("", raw_gate_text, page_title, has_password_form, has_captcha_widget, 0)
            return None, "RESTRICTED" if wall else "FAILED", page_title, publisher, wall or "no_body_element"

        # Compute hyperlink dominance only for unfiltered <body> fallback pages
        total_elem_text = clean_text(main_elem.get_text(separator=" ", strip=True))
        link_text_len = sum(len(a.get_text(" ", strip=True)) for a in main_elem.find_all("a"))
        link_ratio = (link_text_len / max(len(total_elem_text), 1)) if total_elem_text else 0.0

        seen_blocks = set()
        extracted_blocks = []
        substantive_p_count = 0

        for node in main_elem.find_all(["p", "h1", "h2", "h3", "blockquote", "li"]):
            block = clean_text(node.get_text(" ", strip=True))
            if not block:
                continue
            # Ignore short bullet items that are typically navigation menu links
            if node.name == "li" and len(block) <= 35:
                continue
            if len(block) <= 20 and node.name not in ("h1", "h2", "h3"):
                continue
            block_key = block.lower()
            if block_key in seen_blocks:
                continue
            seen_blocks.add(block_key)
            extracted_blocks.append(block)
            if node.name == "p" and len(block) >= 40:
                substantive_p_count += 1

        text = "\n\n".join(extracted_blocks)
        if not text:
            text = total_elem_text

        cleaned = clean_text(text)
        is_valid, reason = cls._assess_content_quality(
            cleaned_text=cleaned,
            min_content_length=min_content_length,
            page_title=page_title,
            raw_gate_text=raw_gate_text,
            has_password_form=has_password_form,
            has_captcha_widget=has_captcha_widget,
            used_body_fallback=used_body_fallback,
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
            )
            return None, "RESTRICTED" if is_wall else "FAILED", page_title, publisher, reason

        return cleaned, "SUCCESS", page_title, publisher, None

    @staticmethod
    def extract_with_firecrawl(url: str) -> Optional[str]:
        """Scrapes an article/webpage using Firecrawl /v0/scrape without exposing FIRECRAWL_API_KEY."""
        if not settings.FIRECRAWL_API_KEY:
            return None
        try:
            headers = {
                "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
                "Content-Type": "application/json",
            }
            with borrow_http_client(timeout_seconds=10.0, connect_timeout=4.0, follow_redirects=False) as client:
                res = client.post(
                    "https://api.firecrawl.dev/v0/scrape",
                    headers=headers,
                    json={"url": url, "pageOptions": {"onlyMainContent": True}},
                )
                if res.status_code == 200:
                    data = res.json()
                    return data.get("data", {}).get("markdown") or data.get("data", {}).get("content")
                logger.warning(f"Firecrawl scrape returned HTTP {res.status_code} for {url}")
        except Exception as e:
            safe_err = _redact_api_key(str(e))
            logger.warning(f"Firecrawl scrape failed for {url} ({type(e).__name__}): {safe_err}")
        return None

    @classmethod
    def _extract_with_httpx(
        cls,
        url: str,
        min_content_length: int,
    ) -> Tuple[Optional[str], str, Optional[str], Optional[str], Optional[str]]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            with borrow_http_client(timeout_seconds=7.0, connect_timeout=3.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code in (401, 403, 429):
                    logger.warning(f"HTTPX extraction restricted (HTTP {resp.status_code}) for URL: {url}")
                    return None, "RESTRICTED", None, None, f"http_{resp.status_code}"
                if resp.status_code != 200:
                    logger.warning(f"HTTPX returned HTTP {resp.status_code} for URL: {url}")
                    return None, "FAILED", None, None, f"http_{resp.status_code}"

                headers_map = getattr(resp, "headers", None) or {}
                ctype = str(headers_map.get("content-type", "")).lower()
                if ctype and "html" not in ctype and "text/" not in ctype and "xml" not in ctype:
                    logger.info(f"HTTPX skipping non-HTML content-type ({ctype}) for URL: {url}")
                    return None, "FAILED", None, None, f"non_html:{ctype.split(';')[0]}"

                return cls._parse_and_validate_html(resp.text, min_content_length=min_content_length)
        except httpx.HTTPError as e:
            logger.warning(f"HTTPX network error extracting {url} ({type(e).__name__}): {e}")
            return None, "RESTRICTED", None, None, f"network_error:{type(e).__name__}"
        except Exception as e:
            logger.error(f"Unexpected HTTPX error extracting {url} ({type(e).__name__}): {e}")
            return None, "FAILED", None, None, f"unexpected_error:{type(e).__name__}"

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
        method = _last_extraction_method_var.get() or ("failed" if status != "SUCCESS" else "httpx")
        return text, status, page_title, publisher, method

    @staticmethod
    def _firecrawl_skip_reason(url: str, httpx_status: str, reject_reason: Optional[str]) -> Optional[str]:
        """Returns a skip label when Firecrawl fallback is guaranteed to fail or waste quota."""
        if reject_reason in ("http_404", "http_410"):
            return "non_existent_page"
        if reject_reason and reject_reason.startswith("non_html:") and any(
            mime in reject_reason for mime in ("image/", "video/", "audio/", "application/octet-stream", "application/zip")
        ):
            return "binary_non_html"

        host = (urlparse(url).netloc or "").lower()
        if any(host == d or host.endswith(f".{d}") for d in _GATED_SOCIAL_HOSTS):
            reason = reject_reason or ""
            if (
                httpx_status == "RESTRICTED"
                or reason.startswith(("http_401", "http_403", "http_429", "http_999", "insufficient_words", "text_too_short", "navigation_heavy"))
                or reason in ("blocked_title", "login_form", "bot_or_login_wall", "restricted_gate_text")
            ):
                return "gated_social_host"
        return None

    @classmethod
    def extract_article(
        cls,
        url: str,
        min_content_length: Optional[int] = None,
    ) -> Tuple[Optional[str], str, Optional[str], Optional[str]]:
        """
        Prioritizes free HTTPX + BeautifulSoup extraction with quality checks,
        falling back to Firecrawl only when HTTPX fails, is restricted, or lacks valid content.
        Returns (content_text, extraction_status, page_title, publisher).
        """
        min_len = min_content_length if min_content_length is not None else settings.ARTICLE_MIN_CONTENT_LENGTH

        # 1. Try free HTTPX + BeautifulSoup + quality validation first
        httpx_text, httpx_status, page_title, publisher, reject_reason = cls._extract_with_httpx(
            url,
            min_content_length=min_len,
        )
        if httpx_text and httpx_status == "SUCCESS":
            _last_extraction_method_var.set("httpx")
            logger.info(f"Article extraction succeeded via method=httpx for {url} ({len(httpx_text)} chars)")
            return httpx_text, "SUCCESS", page_title, publisher

        skip_reason = cls._firecrawl_skip_reason(url, httpx_status, reject_reason)
        if skip_reason:
            logger.info(
                f"Skipping Firecrawl fallback ({skip_reason}, reason={reject_reason}) for {url} (method=failure)"
            )
            _last_extraction_method_var.set("failed")
            final_status = "RESTRICTED" if (httpx_status == "RESTRICTED" or reject_reason == "http_999") else "FAILED"
            safe_title = None if final_status == "RESTRICTED" else page_title
            return None, final_status, safe_title, publisher

        # 2. Fall back to Firecrawl only when HTTPX failed, was restricted, or content quality was insufficient
        if settings.FIRECRAWL_API_KEY:
            logger.info(
                f"HTTPX extraction did not qualify (status={httpx_status}, reason={reject_reason}) "
                f"for {url}; attempting fallback via method=firecrawl"
            )
            fc_raw = cls.extract_with_firecrawl(url)
            fc_cleaned = clean_text(fc_raw) if fc_raw else ""
            if fc_cleaned:
                fc_wall = cls._detect_wall_reason(fc_cleaned, fc_cleaned, None, False, False, 2)
                if not fc_wall:
                    safe_title = None if httpx_status == "RESTRICTED" else page_title
                    _last_extraction_method_var.set("firecrawl")
                    logger.info(
                        f"Article extraction succeeded via method=firecrawl for {url} ({len(fc_cleaned)} chars)"
                    )
                    return fc_cleaned, "SUCCESS", safe_title, publisher
                logger.warning(f"Firecrawl returned gated/blocked content ({fc_wall}) for {url}")
            logger.warning(
                f"Article extraction failed via method=failure (httpx reason={reject_reason}, firecrawl empty/failed) for {url}"
            )
        else:
            logger.warning(
                f"Article extraction failed via method=failure (httpx reason={reject_reason}, FIRECRAWL_API_KEY unset) for {url}"
            )

        _last_extraction_method_var.set("failed")
        safe_title = None if httpx_status == "RESTRICTED" else page_title
        return None, httpx_status, safe_title, publisher
