import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Optional, Tuple
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import IpBlocked, NoTranscriptFound, RequestBlocked
from openai import OpenAI
from backend.config import settings
from backend.utils.http_pool import borrow_http_client
from backend.utils.url_validator import extract_youtube_video_id
from backend.utils.text_cleaner import clean_text
from backend.utils.logger import logger


class _BoundedTimeoutSession(requests.Session):
    """Requests session enforcing a bounded default HTTP timeout for YouTubeTranscriptApi calls."""

    def __init__(self, timeout: float = 5.0):
        super().__init__()
        self._default_timeout = timeout

    def request(self, method, url, *args, **kwargs):
        kwargs.setdefault("timeout", self._default_timeout)
        return super().request(method, url, *args, **kwargs)


class TranscriptExtractor:
    """Extracts available video captions/transcripts or transcribes using Whisper AI."""

    _transcript_ip_block_until: float = 0.0
    _TRANSCRIPT_BLOCK_COOLDOWN_SEC: float = 20.0

    @classmethod
    def clear_transcript_cooldown(cls) -> None:
        """Resets any active YouTube transcript IP-block cooldown."""
        cls._transcript_ip_block_until = 0.0

    @staticmethod
    def _is_ip_block_error(exc: Exception) -> bool:
        if isinstance(exc, (RequestBlocked, IpBlocked)):
            return True
        if type(exc).__name__ in ("RequestBlocked", "IpBlocked"):
            return True
        return "blocking requests from your ip" in str(exc).lower()

    @staticmethod
    def _transcribe_with_whisper(video_url: str, max_duration_sec: int = 600) -> Optional[str]:
        """Downloads audio snippet and transcribes using Groq Whisper or OpenAI Whisper."""
        api_key = settings.GROQ_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            return None

        ytdlp_bin = shutil.which("yt-dlp")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            cmd = [ytdlp_bin] if ytdlp_bin else [sys.executable, "-m", "yt_dlp"]
            cmd.extend([
                "-f", "ba[abr<=64]/ba/b",
                "--extract-audio",
                "--audio-format", "mp3",
                "--download-sections", f"*00:00-{max_duration_sec // 60:02d}:{max_duration_sec % 60:02d}",
                "-o", tmp_path,
                "--no-warnings",
                video_url
            ])
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
            if res.returncode != 0 or not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                return None

            # Transcribe with Groq or OpenAI Whisper
            if settings.GROQ_API_KEY:
                client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
                model = "whisper-large-v3-turbo"
            else:
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                model = "whisper-1"

            with open(tmp_path, "rb") as audio_file:
                transcript = client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    response_format="text"
                )
            return clean_text(str(transcript))
        except Exception as e:
            logger.info(f"Whisper STT fallback failed for {video_url}: {e}")
            return None
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    @staticmethod
    def _extract_video_metadata_fast(video_url: str) -> Optional[str]:
        """Extracts video description cleanly from YouTube watch HTML without spawning yt-dlp."""
        video_id = extract_youtube_video_id(video_url)
        if not video_id:
            return None
        try:
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            with borrow_http_client(timeout_seconds=4.5, connect_timeout=2.5, follow_redirects=True) as client:
                resp = client.get(
                    watch_url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                        ),
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                )
            if resp.status_code != 200 or not resp.text:
                return None

            match = re.search(r'"shortDescription"\s*:\s*"', resp.text)
            if match:
                quote_start = match.end() - 1
                desc, _ = json.JSONDecoder().raw_decode(resp.text, quote_start)
                cleaned = clean_text(str(desc))
                if cleaned and len(cleaned) >= 30:
                    return cleaned

            meta_match = re.search(
                r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)["\']',
                resp.text,
                re.IGNORECASE,
            )
            if meta_match:
                meta_desc = clean_text(html.unescape(meta_match.group(1)))
                if (
                    meta_desc
                    and len(meta_desc) >= 30
                    and "share your videos with friends" not in meta_desc.lower()
                ):
                    return meta_desc
        except Exception:
            return None
        return None

    @staticmethod
    def _extract_video_metadata(video_url: str, skip_watch_html: bool = False) -> Optional[str]:
        """Extracts rich video description and chapter markers via fast watch HTML or yt-dlp fallback."""
        if not skip_watch_html:
            fast_desc = TranscriptExtractor._extract_video_metadata_fast(video_url)
            if fast_desc:
                return fast_desc

        ytdlp_bin = shutil.which("yt-dlp")
        cmd = [ytdlp_bin] if ytdlp_bin else [sys.executable, "-m", "yt_dlp"]
        cmd.extend([
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            "--socket-timeout", "5",
            video_url
        ])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=7)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                desc = data.get("description") or ""
                chapters = data.get("chapters") or []
                lines = []
                if desc:
                    lines.append(desc.strip())
                if chapters:
                    lines.append("\nVideo Topics & Chapters:")
                    for ch in chapters:
                        start_sec = int(ch.get("start_time", 0))
                        lines.append(f"- {ch.get('title')} ({start_sec // 60:02d}:{start_sec % 60:02d})")
                return "\n".join(lines).strip() or None
        except Exception:
            pass
        return None

    @classmethod
    def extract_transcript(cls, video_url: str, allow_whisper: bool = True) -> Tuple[Optional[str], str]:
        """
        Returns (transcript_text, extraction_status).
        Statuses: SUCCESS, AI_TRANSCRIBED, METADATA_FALLBACK, or TRANSCRIPT_UNAVAILABLE.
        """
        video_id = extract_youtube_video_id(video_url)
        if not video_id:
            return None, "FAILED"

        skip_watch_html = time.monotonic() < cls._transcript_ip_block_until

        # Tier 1: Try YouTube native auto-captions / subtitles across multiple languages
        if not skip_watch_html:
            try:
                preferred_languages = ["en", "en-US", "en-GB", "en-IN", "hi", "hi-Latn"]
                if hasattr(YouTubeTranscriptApi, "get_transcript"):
                    try:
                        transcript_entries = YouTubeTranscriptApi.get_transcript(
                            video_id, languages=preferred_languages
                        )
                    except NoTranscriptFound:
                        transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
                else:
                    try:
                        yt_api = YouTubeTranscriptApi(http_client=_BoundedTimeoutSession(timeout=5.0))
                    except TypeError:
                        yt_api = YouTubeTranscriptApi()
                    try:
                        fetched = yt_api.fetch(video_id, languages=preferred_languages)
                        transcript_entries = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else fetched
                    except NoTranscriptFound:
                        transcript_list = yt_api.list(video_id)
                        first_transcript = next(iter(transcript_list), None)
                        if first_transcript:
                            fetched = first_transcript.fetch()
                            transcript_entries = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else fetched
                        else:
                            raise

                formatted_lines = []
                for entry in transcript_entries:
                    start_val = entry.get("start", 0) if isinstance(entry, dict) else getattr(entry, "start", 0)
                    text_val = entry.get("text", "") if isinstance(entry, dict) else getattr(entry, "text", "")
                    start_sec = int(start_val)
                    mins = start_sec // 60
                    secs = start_sec % 60
                    text = str(text_val).replace("\n", " ").strip()
                    formatted_lines.append(f"[{mins:02d}:{secs:02d}] {text}")

                transcript_text = "\n".join(formatted_lines)
                return transcript_text, "SUCCESS"
            except Exception as e:
                if cls._is_ip_block_error(e):
                    cls._transcript_ip_block_until = time.monotonic() + cls._TRANSCRIPT_BLOCK_COOLDOWN_SEC
                    skip_watch_html = True
                    logger.info(
                        f"YouTube transcripts IP-blocked ({type(e).__name__}); skipping watch HTML refetch for {video_id}"
                    )
                else:
                    msg_summary = (str(e).strip().splitlines() or [type(e).__name__])[0][:180]
                    logger.info(f"YouTube native captions unavailable for {video_id}: {msg_summary}")

        # Tier 2: AI Speech-to-Text Transcription via Groq Whisper or OpenAI Whisper
        if allow_whisper:
            whisper_text = cls._transcribe_with_whisper(video_url)
            if whisper_text:
                return whisper_text, "AI_TRANSCRIBED"

        # Tier 3: Zero-credential rich metadata & chapter extraction
        try:
            metadata_text = cls._extract_video_metadata(video_url, skip_watch_html=skip_watch_html)
        except TypeError:
            metadata_text = cls._extract_video_metadata(video_url)
        if metadata_text:
            return metadata_text, "METADATA_FALLBACK"

        return None, "TRANSCRIPT_UNAVAILABLE"

