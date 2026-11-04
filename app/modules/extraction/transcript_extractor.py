from typing import Optional, Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from app.utils.url_validator import extract_youtube_video_id
from app.utils.logger import logger


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
            # Attempt to fetch manual or auto-generated transcripts
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            formatted_lines = []
            for entry in transcript_list:
                start_sec = int(entry.get("start", 0))
                mins = start_sec // 60
                secs = start_sec % 60
                text = entry.get("text", "").replace("\n", " ").strip()
                formatted_lines.append(f"[{mins:02d}:{secs:02d}] {text}")

            transcript_text = "\n".join(formatted_lines)
            return transcript_text, "SUCCESS"
        except Exception as e:
            # Captions might be disabled, video private, or auto-subs not generated
            logger.info(f"Subtitles/Transcript not available for {video_id}: {e}")
            return None, "TRANSCRIPT_UNAVAILABLE"

