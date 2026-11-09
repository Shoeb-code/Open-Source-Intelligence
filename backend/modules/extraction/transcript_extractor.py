from typing import Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from backend.utils.url_validator import extract_youtube_video_id
from backend.utils.logger import logger


class TranscriptExtractor:
    """Extracts available video captions/transcripts from YouTube videos."""

    @staticmethod
    def extract_transcript(video_url: str) -> Tuple[Optional[str], str]:
        """
        Returns (transcript_text, extraction_status).
        Status is SUCCESS, TRANSCRIPT_UNAVAILABLE, or FAILED.
        """
        video_id = extract_youtube_video_id(video_url)
        if not video_id:
            return None, "FAILED"

        try:
            # Check for YouTubeTranscriptApi classmethod vs modern instance fetch
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
                    # Fallback to any transcript available on the video
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
            # Captions might be disabled, video private, or auto-subs not generated
            logger.info(f"Subtitles/Transcript not available for {video_id}: {e}")
            return None, "TRANSCRIPT_UNAVAILABLE"

