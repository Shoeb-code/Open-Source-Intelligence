from collections import Counter
from datetime import datetime, timezone
from typing import List, Dict, Any
from backend.database.models import Person, Appearance


class ReportGenerator:
    """Consolidates verified appearances and AI analysis into a structured intelligence report."""

    @staticmethod
    def generate_report(person: Person, appearances: List[Appearance]) -> Dict[str, Any]:
        # Filter for non-rejected candidate appearances
        valid_appearances = [a for a in appearances if a.identity_status in ("VERIFIED", "LIKELY_MATCH", "NEEDS_REVIEW")]
        
        # 1. Statistics
        type_counts = Counter([a.appearance_type for a in valid_appearances])
        total_sources = sum(len(a.sources) for a in appearances)
        
        stats = {
            "total_appearances_discovered": len(appearances),
            "verified_appearances": len([a for a in appearances if a.identity_status == "VERIFIED"]),
            "likely_matches": len([a for a in appearances if a.identity_status == "LIKELY_MATCH"]),
            "needs_review": len([a for a in appearances if a.identity_status == "NEEDS_REVIEW"]),
            "rejected": len([a for a in appearances if a.identity_status == "REJECTED"]),
            "total_distinct_sources": total_sources,
            "by_type": dict(type_counts)
        }

        # 2. Chronological Timeline with safe offset-naive and offset-aware normalization
        def _get_sort_datetime(a: Appearance) -> datetime:
            dt = a.published_at or a.created_at
            if dt is None:
                return datetime.min.replace(tzinfo=timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)

        timeline = []
        dated_appearances = sorted(
            valid_appearances,
            key=_get_sort_datetime,
            reverse=True
        )
        for a in dated_appearances:
            timeline.append({
                "appearance_id": a.id,
                "date": a.published_at.isoformat() if a.published_at else a.created_at.isoformat(),
                "title": a.title,
                "appearance_type": a.appearance_type,
                "publisher": a.publisher,
                "summary": a.analysis.summary if a.analysis else None,
                "confidence_score": a.confidence_score,
                "primary_source_url": a.sources[0].source_url if a.sources else None
            })

        # 3. Recurring Topics & Themes
        all_topics = []
        all_evidence = []
        for a in valid_appearances:
            if a.analysis:
                if a.analysis.topics:
                    all_topics.extend(a.analysis.topics)
                if a.analysis.evidence:
                    for ev in a.analysis.evidence:
                        all_evidence.append({
                            "statement": ev,
                            "source_title": a.title,
                            "publisher": a.publisher,
                            "appearance_id": a.id
                        })

        topic_freq = [
            {"topic": item[0], "count": item[1]}
            for item in Counter(all_topics).most_common(10)
        ]

        # 4. Executive Summary
        exec_summary = (
            f"Public Appearance Intelligence Report for {person.name} ({person.profession or 'Professional'}). "
            f"A total of {len(valid_appearances)} verified/likely public appearances were identified across "
            f"{len(set(a.publisher for a in valid_appearances if a.publisher))} unique publishers and media outlets. "
            f"Dominant themes include: {', '.join([t['topic'] for t in topic_freq[:4]]) or 'various industry topics'}."
        )

        return {
            "person": {
                "id": person.id,
                "name": person.name,
                "profession": person.profession,
                "biography": person.biography
            },
            "executive_summary": exec_summary,
            "statistics": stats,
            "timeline": timeline,
            "recurring_topics": topic_freq,
            "important_statements": all_evidence[:15],
            "limitations_and_coverage": (
                "Only publicly accessible sources were analyzed. Private or restricted media "
                "behind authentication barriers or without accessible captions/text are omitted."
            ),
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
