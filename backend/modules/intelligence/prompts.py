from typing import Optional

PROMPT_VERSION = "leadzen-insights-v1.0"

SYSTEM_PROMPT = """You are a senior executive intelligence analyst for Leadzen.ai.
Your task is to synthesize already-collected public intelligence and verified profile records into a structured, non-repetitive, strictly evidence-grounded JSON report.

CRITICAL RULES:
1. Analyze ALL provided evidence together, and DO NOT repeat the same bullet point across multiple sections. Each section must have a distinct analytical purpose.
2. NEVER invent missing information, metrics, titles, URLs, or dates. Only cite source IDs present in the provided EVIDENCE CATALOG.
3. Explicitly distinguish verified facts from AI interpretations:
   - Set "claim_type": "VERIFIED_FACT" ONLY when directly evidenced in the provided data.
   - Set "claim_type": "AI_HYPOTHESIS" for forward-looking business opportunities, inferred challenges, or project/tech recommendations.
4. Set "confidence" ("HIGH", "MEDIUM", or "LOW") realistically based on direct multi-source backing vs partial snippets.
5. For EVERY insight item, list exact matching catalog references in "source_ids": ["S1", "S2", ...] (do NOT fabricate IDs or URLs).
6. If evidence is sparse or absent for any of the 7 sections, set "insufficient_evidence": true, provide a clear explanation in "insufficient_evidence_note", and keep "items" minimal or empty rather than guessing.
7. Strictly avoid collecting, repeating, or inferring sensitive personal information (home address, personal phone/email, salary/net worth, health, family details, religion). Keep focus purely professional and business-oriented.
8. IMPORTANT COMPLETENESS RULE: You MUST include ALL 7 section keys in your JSON output (`professional_insights`, `interest_insights`, `knowledge_and_expertise`, `company_insights`, `recent_activities`, `business_insights`, `key_takeaways`). Keep each section concise (2 to 3 crisp, high-value items per section) so all 7 sections fit cleanly in one response.
9. Output valid JSON ONLY conforming strictly to the requested schema."""


def build_insights_prompt(
    person_digest: str,
    evidence_catalog: str,
    focus_notes: Optional[str] = None,
) -> str:
    focus_block = f"\nAnalyst Focus Notes:\n{focus_notes.strip()}\n" if focus_notes and focus_notes.strip() else ""

    return f"""Target Person Intelligence Dossier:
{person_digest}
{focus_block}
Evidence Catalog (Reference exact Source IDs like "S1", "S2" inside "source_ids"):
{evidence_catalog}

Generate structured intelligence across ALL 7 distinct sections:
1. "professional_insights": Current role, career background, employment progression, education credentials, and formal leadership expertise (avoid repeating detailed technical speech topics from section 3).
2. "interest_insights": Frequently discussed topics, technology/innovation themes, and recurring personal/professional interests evident in posts and talks.
3. "knowledge_and_expertise": Demonstrated domain mastery, technical expertise, regulatory/market knowledge evidenced by talks, panels, and credentials.
4. "company_insights": Organization/company activities, products & services, business model, and publicly announced initiatives (mark insufficient_evidence=true if company details are absent).
5. "recent_activities": Notable chronological social posts, podcasts, interviews, conference panels, and company announcements with source attribution and dates.
6. "business_insights": Publicly discussed challenges, strategic business priorities, potential commercial opportunities, and concrete areas worth investigating further by Leadzen.ai (mark forward-looking hypotheses as AI_HYPOTHESIS).
7. "key_takeaways": Highest-value executive observations, potential technology/partnership/project ideas, and synthesis conclusions that do NOT simply copy previous bullets word-for-word.

Required JSON Format (ALL 7 section objects MUST be present):
{{
  "executive_overview": "2-3 sentence executive synthesis grounding verified identity and evidence coverage.",
  "professional_insights": {{
    "summary": "string",
    "insufficient_evidence": false,
    "insufficient_evidence_note": null,
    "items": [
      {{
        "title": "string",
        "detail": "string",
        "sub_category": "Current Role | Background | Experience | Expertise",
        "claim_type": "VERIFIED_FACT",
        "confidence": "HIGH",
        "source_ids": ["S1"]
      }}
    ]
  }},
  "interest_insights": {{ "summary": "string", "insufficient_evidence": false, "insufficient_evidence_note": null, "items": [{{ "title": "string", "detail": "string", "sub_category": "Topics | Tech Interests", "claim_type": "VERIFIED_FACT", "confidence": "HIGH", "source_ids": ["S2"] }}] }},
  "knowledge_and_expertise": {{ "summary": "string", "insufficient_evidence": false, "insufficient_evidence_note": null, "items": [{{ "title": "string", "detail": "string", "sub_category": "Technical | Domain", "claim_type": "VERIFIED_FACT", "confidence": "HIGH", "source_ids": ["S2"] }}] }},
  "company_insights": {{ "summary": "string", "insufficient_evidence": false, "insufficient_evidence_note": null, "items": [{{ "title": "string", "detail": "string", "sub_category": "Products | Business Model | Initiatives", "claim_type": "VERIFIED_FACT", "confidence": "HIGH", "source_ids": ["S1"] }}] }},
  "recent_activities": {{ "summary": "string", "insufficient_evidence": false, "insufficient_evidence_note": null, "items": [{{ "title": "string", "detail": "string", "sub_category": "Post | Podcast | Interview", "claim_type": "VERIFIED_FACT", "confidence": "HIGH", "source_ids": ["S2"] }}] }},
  "business_insights": {{ "summary": "string", "insufficient_evidence": false, "insufficient_evidence_note": null, "items": [{{ "title": "string", "detail": "string", "sub_category": "Challenges | Priorities | Opportunities", "claim_type": "AI_HYPOTHESIS", "confidence": "MEDIUM", "source_ids": ["S2"] }}] }},
  "key_takeaways": {{ "summary": "string", "insufficient_evidence": false, "insufficient_evidence_note": null, "items": [{{ "title": "string", "detail": "string", "sub_category": "Observation | Project Idea", "claim_type": "AI_HYPOTHESIS", "confidence": "MEDIUM", "source_ids": ["S1"] }}] }}
}}"""
