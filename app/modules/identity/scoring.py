from typing import Dict, Any, Tuple
from rapidfuzz import fuzz
from app.modules.persons.schemas import IdentityContext
from app.modules.extraction.metadata_extractor import ExtractedPayload


class IdentityScorer:
    """Calculates multi-signal identity matching scores using fuzzy string comparison and context evidence."""

    @staticmethod
    def calculate_score(context: IdentityContext, payload: ExtractedPayload) -> Tuple[float, Dict[str, Any]]:
        target_name = context.name.lower()
        search_corpus = f"{payload.title} {payload.description or ''} {payload.extracted_content or ''}".lower()

        signals: Dict[str, Any] = {
            "name_match": 0.0,
            "organization_match": 0.0,
            "role_match": 0.0,
            "handle_match": 0.0,
            "matched_signals": []
        }

        # 1. Name Match (Weight: 0.50)
        # Check token_set_ratio and exact presence
        if target_name in search_corpus:
            name_score = 1.0
            signals["matched_signals"].append("exact_name_in_corpus")
        else:
            fuzzy_ratio = fuzz.partial_ratio(target_name, payload.title.lower())
            name_score = min(fuzzy_ratio / 100.0, 0.85) if fuzzy_ratio > 70 else 0.0

        signals["name_match"] = round(name_score, 2)

        # If name has negligible match, score drops to near zero to prevent false positives
        if name_score < 0.60:
            return 0.1, signals

        # 2. Organization Match (Weight: 0.25)
        org_score = 0.0
        for org in context.organizations:
            if org.lower() in search_corpus:
                org_score = 1.0
                signals["matched_signals"].append(f"organization:{org}")
                break
        signals["organization_match"] = round(org_score, 2)

        # 3. Profession / Role Match (Weight: 0.15)
        role_score = 0.0
        if context.profession:
            prof_tokens = [w for w in context.profession.lower().split() if len(w) > 3]
            matched_tokens = [w for w in prof_tokens if w in search_corpus]
            if matched_tokens:
                role_score = min(len(matched_tokens) / len(prof_tokens), 1.0)
                signals["matched_signals"].append(f"role_tokens:{','.join(matched_tokens)}")
        signals["role_match"] = round(role_score, 2)

        # 4. Known Usernames / Handles (Weight: 0.10)
        handle_score = 0.0
        for handle in context.known_usernames:
            if handle.lower() in search_corpus or handle.lower() in payload.canonical_url.lower():
                handle_score = 1.0
                signals["matched_signals"].append(f"handle:{handle}")
                break
        signals["handle_match"] = round(handle_score, 2)

        # Weighted calculation
        total_score = (
            0.50 * name_score +
            0.25 * org_score +
            0.15 * role_score +
            0.10 * handle_score
        )

        final_score = round(min(max(total_score, 0.0), 1.0), 2)
        return final_score, signals

