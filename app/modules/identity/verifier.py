from typing import Tuple, Dict, Any
from app.modules.persons.schemas import IdentityContext
from app.modules.extraction.metadata_extractor import ExtractedPayload
from app.modules.identity.scoring import IdentityScorer


class IdentityVerifier:
    """Verifies candidate appearance against target identity using multi-signal threshold gates."""

    @staticmethod
    def verify(context: IdentityContext, payload: ExtractedPayload) -> Tuple[str, float, Dict[str, Any]]:
        """
        Returns (identity_status, confidence_score, evidence_signals).
        Statuses: VERIFIED, LIKELY_MATCH, NEEDS_REVIEW, REJECTED.
        """
        score, signals = IdentityScorer.calculate_score(context, payload)

        if score >= 0.80:
            status = "VERIFIED"
        elif score >= 0.55:
            status = "LIKELY_MATCH"
        elif score >= 0.35:
            status = "NEEDS_REVIEW"
        else:
            status = "REJECTED"

        return status, score, signals

