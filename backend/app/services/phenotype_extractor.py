"""
Phenotype Extractor Agent
=========================
Converts free-text clinical descriptions (patient + parents) into standardized
HPO terms, following the DeepRare two-step approach:

  1. Extract candidate phenotype phrases from free text
       - LLM extraction when an LLM is configured
       - Rule-based clinical-phrase extraction as fallback
  2. Normalize each phrase to an HPO term via BioLORD cosine similarity
       (delegated to hpo_service / hpo_ontology)

Produces an HPO profile for the patient and, separately, for each parent.
"""

import re
import logging

from app.services.hpo_service import symptoms_to_hpo, LOCAL_HPO_MAP
from app.services.llm_service import llm_extract_hpo
from app.core.config import settings

logger = logging.getLogger(__name__)


# Clinical phrase patterns — used by the rule-based fallback extractor.
# These catch multi-word clinical findings that single-keyword search misses.
_CLINICAL_TERMS = sorted(LOCAL_HPO_MAP.keys(), key=len, reverse=True)


async def extract_phenotypes(
    symptoms: list[str] | None,
    clinical_text: str | None,
) -> list[dict]:
    """
    Build an HPO profile from explicit symptom tags + free-text notes.
    Returns deduplicated list of {term, hpo_id, source, score}.
    """
    phrases: list[str] = []

    # 1. Explicit symptom tags
    if symptoms:
        phrases.extend([s.strip() for s in symptoms if s and s.strip()])

    # 2. Extract from free text
    if clinical_text and clinical_text.strip():
        extracted = await _extract_phrases(clinical_text)
        phrases.extend(extracted)

    # Dedup phrases (case-insensitive)
    seen = set()
    unique_phrases = []
    for p in phrases:
        k = p.lower().strip()
        if k and k not in seen:
            seen.add(k)
            unique_phrases.append(p)

    if not unique_phrases:
        return []

    # 3. Normalize all phrases to HPO terms (BioLORD cosine inside)
    hpo_terms = await symptoms_to_hpo(unique_phrases)

    return [
        {
            "term": t.get("name", t.get("original_symptom", "")),
            "original": t.get("original_symptom", ""),
            "hpo_id": t.get("id", ""),
            "source": t.get("source", ""),
            "score": round(float(t.get("score", 0.0)), 3),
        }
        for t in hpo_terms
    ]


async def extract_parent_phenotypes(patient_data: dict) -> dict:
    """Extract HPO profiles for father and mother from their phenotype text."""
    result = {}
    for parent in ("father", "mother"):
        pdata = patient_data.get(parent) or {}
        text_parts = []
        if pdata.get("phenotype_description"):
            text_parts.append(pdata["phenotype_description"])
        if pdata.get("known_conditions"):
            text_parts.append(pdata["known_conditions"])
        text = ". ".join(text_parts)
        if text.strip():
            result[parent] = await extract_phenotypes(None, text)
        else:
            result[parent] = []
    return result


async def _extract_phrases(text: str) -> list[str]:
    """Extract candidate phenotype phrases from free text."""
    # 1. LLM extraction (best — when configured)
    if not settings.MOCK_MODE and (settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY):
        try:
            terms = await llm_extract_hpo(text)
            if terms:
                return terms
        except Exception as e:
            logger.debug(f"LLM phrase extraction failed: {e}")

    # 2. Rule-based fallback: match known clinical terms + simple noun phrases
    return _rule_based_extract(text)


def _rule_based_extract(text: str) -> list[str]:
    text_lower = text.lower()
    found: list[str] = []

    # Match known clinical terms (longest first to prefer multi-word)
    for term in _CLINICAL_TERMS:
        if term in text_lower:
            found.append(term)

    # Also split sentences and grab short clinical-looking fragments
    # (e.g. "elevated liver enzymes", "low ceruloplasmin")
    fragments = re.split(r"[.;,\n]", text)
    for frag in fragments:
        frag = frag.strip()
        # Heuristic: 2-5 word fragments that look like findings
        words = frag.split()
        if 1 <= len(words) <= 5 and not frag.lower() in [f.lower() for f in found]:
            # Skip generic/non-clinical fragments
            if any(w in frag.lower() for w in [
                "elevated", "low", "high", "abnormal", "decreased", "increased",
                "enlarged", "delayed", "recurrent", "chronic", "severe", "mild",
                "bilateral", "progressive", "absent", "reduced",
            ]):
                found.append(frag)

    # Dedup
    seen = set()
    out = []
    for f in found:
        k = f.lower().strip()
        if k and k not in seen:
            seen.add(k)
            out.append(f)
    return out
