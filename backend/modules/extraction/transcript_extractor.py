import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
from backend.config import settings
from backend.utils.url_validator import extract_youtube_video_id
from backend.utils.text_cleaner import clean_text
from backend.utils.logger import logger


class TranscriptExtractor:
    """Extracts available video captions/transcripts or transcribes using Whisper AI."""

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
    def _extract_video_metadata(video_url: str) -> Optional[str]:
        """Extracts rich video description and chapter markers using yt-dlp."""
        ytdlp_bin = shutil.which("yt-dlp")
        cmd = [ytdlp_bin] if ytdlp_bin else [sys.executable, "-m", "yt_dlp"]
        cmd.extend([
            "--dump-single-json",
            "--skip-download",
            "--no-warnings",
            video_url
        ])
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
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

        # Tier 1: Try YouTube native auto-captions / subtitles across multiple languages
        try:
            preferred_languages = ["en", "en-US", "en-GB", "en-IN", "hi", "hi-Latn"]
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                try:
                    transcript_entries = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=preferred_languages
                    )
                except Exception:
                    transcript_entries = YouTubeTranscriptApi.get_transcript(video_id)
            else:
                yt_api = YouTubeTranscriptApi()
                try:
                    fetched = yt_api.fetch(video_id, languages=preferred_languages)
                    transcript_entries = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else fetched
                except Exception:
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
            logger.info(f"YouTube native captions unavailable for {video_id}: {e}")

        # Tier 2: AI Speech-to-Text Transcription via Groq Whisper or OpenAI Whisper
        if allow_whisper:
            whisper_text = cls._transcribe_with_whisper(video_url)
            if whisper_text:
                return whisper_text, "AI_TRANSCRIBED"

        # Tier 3: Zero-credential rich metadata & chapter extraction
        metadata_text = cls._extract_video_metadata(video_url)
        if metadata_text:
            return metadata_text, "METADATA_FALLBACK"

        return None, "TRANSCRIPT_UNAVAILABLE"

