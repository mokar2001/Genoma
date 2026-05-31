"""
LLM Service — configurable provider.
Supports OpenAI, Anthropic, Groq, Ollama (any OpenAI-compatible endpoint).

Small model support (Ollama/qwen2.5:1.5b):
  - json_mode disabled (small models don't support response_format)
  - Simpler, shorter prompts
  - Robust JSON extraction from free-text responses
"""
import json
import re
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

DIAGNOSIS_SYSTEM_PROMPT = (
    "You are a rare disease diagnostic AI. "
    "Respond ONLY with valid JSON. No explanation outside the JSON."
)


def _is_ollama() -> bool:
    """Detect if we're using a local Ollama instance."""
    base = settings.OPENAI_BASE_URL or ""
    return "11434" in base or "ollama" in base.lower()


def _extract_json(text: str) -> dict:
    """
    Robustly extract JSON from LLM free-text output.
    Handles: pure JSON, JSON inside markdown ```json blocks, partial JSON.
    """
    if not text:
        return {}

    # 1. Try direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Extract from ```json ... ``` block
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 3. Find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    # 4. Try to fix truncated JSON by closing brackets
    for end in ["}", "}]}", "}]}}"]:
        try:
            return json.loads(text.rstrip() + end)
        except Exception:
            pass

    logger.warning(f"Could not extract JSON from LLM output: {text[:200]}")
    return {}


def _build_simple_prompt(
    hpo_terms: list[dict],
    variants: list[dict],
    pcf_results: list[dict],
    pbr_results: list[dict],
    suspected: list[str],
    patient_meta: dict,
) -> str:
    """
    Compact prompt for small models (1–3B params).
    Fits in ~512 tokens, asks for minimal but structured JSON.
    """
    hpo_names = [t["name"] for t in hpo_terms if t.get("name")][:8]
    genes = [v.get("gene", "") for v in variants if v.get("gene")][:3]
    pcf_names = [
        r.get("disease_name_en") or r.get("name", "")
        for r in pcf_results[:3]
        if r.get("disease_name_en") or r.get("name")
    ]
    pbr_names = [r.get("disease_name", "") for r in pbr_results[:3] if r.get("disease_name")]

    lines = [
        "Rare disease differential diagnosis. Return JSON only.",
        f"Symptoms: {', '.join(hpo_names) or 'not specified'}",
    ]
    if genes:
        lines.append(f"Genes: {', '.join(genes)}")
    if suspected:
        lines.append(f"Suspected: {', '.join(suspected[:3])}")
    if pcf_names:
        lines.append(f"PubCaseFinder suggests: {', '.join(pcf_names)}")
    if pbr_names:
        lines.append(f"PhenoBrain suggests: {', '.join(pbr_names)}")
    lines.append(
        'Return: {"candidates":[{"disease_name":"...","orpha_code":"ORPHA:...","omim_id":"...","score":0.9,'
        '"phenotype_match_score":0.85,"genotype_match_score":0.8,"prevalence":"1/5000",'
        '"inheritance_pattern":"Autosomal dominant","matched_symptoms":["..."],'
        '"supporting_genes":["..."],"reasoning":"..."}],"reasoning_summary":"..."}'
    )
    lines.append("List top 3 rare diseases. Scores between 0 and 1.")

    return "\n".join(lines)


def _build_full_prompt(
    hpo_terms: list[dict],
    variants: list[dict],
    patient_meta: dict,
    pcf_results: list[dict],
    pbr_results: list[dict],
    suspected: list[str],
    memory_bank: dict,
) -> str:
    """Full prompt for large models (GPT-4, Claude, Llama-70B)."""
    hpo_str = ", ".join([f"{t['name']} ({t['id']})" for t in hpo_terms if t.get("id")])
    var_str = ", ".join([f"{v.get('gene')} {v.get('cdna_change', '')}" for v in variants[:5]])
    pcf_str = ", ".join([r.get("disease_name_en", r.get("name", "")) for r in pcf_results[:5]])
    pbr_str = ", ".join([r.get("disease_name", "") for r in pbr_results[:5]])
    knowledge = memory_bank.get("knowledge", {})
    pubmed_titles = "; ".join(
        a.get("title", "") for a in knowledge.get("pubmed", [])[:2]
    )

    return f"""Analyze this rare disease case. Return ONLY valid JSON.

PATIENT:
- Age: {_calc_age(patient_meta.get('date_of_birth', ''))}
- Sex: {patient_meta.get('sex', 'Unknown')}
- Ethnicity: {patient_meta.get('ethnicity', 'Unknown')}
- Familial pattern: {patient_meta.get('familial_type', 'Unknown')}

HPO TERMS: {hpo_str or 'None'}
VARIANTS: {var_str or 'None'}
SUSPECTED: {', '.join(suspected) or 'None'}
PubCaseFinder: {pcf_str or 'No results'}
PhenoBrain: {pbr_str or 'No results'}
PubMed: {pubmed_titles or 'None'}

Return top-5 diagnoses as:
{{"candidates":[{{"disease_name":"...","orpha_code":"ORPHA:...","omim_id":"...","score":0.95,"phenotype_match_score":0.9,"genotype_match_score":0.85,"prevalence":"1/5000","inheritance_pattern":"Autosomal dominant","matched_symptoms":["symptom1","symptom2"],"unmatched_symptoms":[],"supporting_genes":["GENE1"],"reasoning":"Evidence-based explanation with citations."}}],"reasoning_summary":"..."}}"""


async def llm_diagnose(
    hpo_terms: list[dict],
    variants: list[dict],
    patient_meta: dict,
    pubcasefinder_results: list[dict],
    phenobrain_results: list[dict],
    suspected_diseases: list[str],
    memory_bank: dict,
) -> dict:
    if settings.MOCK_MODE:
        return {"candidates": [], "reasoning_summary": "Mock mode active."}

    # Use compact prompt for small local models
    if _is_ollama():
        prompt = _build_simple_prompt(
            hpo_terms, variants,
            pubcasefinder_results, phenobrain_results,
            suspected_diseases, patient_meta,
        )
    else:
        prompt = _build_full_prompt(
            hpo_terms, variants, patient_meta,
            pubcasefinder_results, phenobrain_results,
            suspected_diseases, memory_bank,
        )

    try:
        if settings.OPENAI_API_KEY:
            return await _call_openai(prompt)
        elif settings.ANTHROPIC_API_KEY:
            return await _call_anthropic(prompt)
    except Exception as e:
        logger.warning(f"LLM diagnose failed: {e}")

    return {"candidates": [], "reasoning_summary": "LLM call failed."}


async def llm_self_reflect(
    candidates: list[dict],
    hpo_terms: list[dict],
    evidence: dict,
) -> dict:
    if settings.MOCK_MODE:
        return {"validated": candidates, "reflection_notes": "Mock."}

    # Skip reflection for small models — too expensive for 1.5B
    if _is_ollama():
        return {"validated": candidates, "reflection_notes": "Skipped for local small model."}

    prompt = f"""Validate these rare disease diagnoses. Return JSON only.
HPO terms: {[t['name'] for t in hpo_terms[:6]]}
Candidates: {[c.get('disease_name') for c in candidates[:3]]}
Return: {{"validated": [...same candidates with updated scores...], "reflection_notes": "..."}}"""

    try:
        if settings.OPENAI_API_KEY:
            result = await _call_openai(prompt)
            if result.get("validated"):
                return result
    except Exception as e:
        logger.debug(f"Self-reflection failed: {e}")

    return {"validated": candidates}


async def llm_extract_hpo(free_text: str) -> list[str]:
    """
    Extract phenotype phrases from free-text clinical description.
    Returns a list of short phenotype phrases (mapped to HPO downstream).
    """
    if settings.MOCK_MODE or not (settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY):
        return []
    if not free_text or not free_text.strip():
        return []

    prompt = (
        "Extract clinical phenotype terms from this text. "
        "Return ONLY a JSON object with a 'terms' array of short phrases "
        '(e.g. {"terms":["aortic root dilation","arachnodactyly"]}).\n\n'
        f"Text: {free_text[:2000]}"
    )

    try:
        if settings.OPENAI_API_KEY:
            result = await _call_openai(prompt)
        elif settings.ANTHROPIC_API_KEY:
            result = await _call_anthropic(prompt)
        else:
            return []

        if isinstance(result, dict):
            terms = result.get("terms") or result.get("phenotypes") or []
            if isinstance(terms, list):
                return [str(t).strip() for t in terms if str(t).strip()]
        if isinstance(result, list):
            return [str(t).strip() for t in result if str(t).strip()]
    except Exception as e:
        logger.debug(f"HPO extraction failed: {e}")
    return []


async def llm_clinical_inquiry(
    patient_data: dict,
    symptoms: list[str],
    preliminary_diseases: list[str],
) -> list[dict]:
    if settings.MOCK_MODE:
        return _mock_clinical_questions(symptoms, preliminary_diseases)

    prompt = (
        f"Generate 3 clinical follow-up questions for rare disease diagnosis.\n"
        f"Symptoms: {', '.join(symptoms[:5])}\n"
        f"Candidate diseases: {', '.join(preliminary_diseases[:2])}\n"
        'Return JSON: [{"question":"...","options":["Yes","No","Unknown"],"hpo_if_yes":"HP:..."}]'
    )

    try:
        if settings.OPENAI_API_KEY:
            result = await _call_openai(prompt)
            if isinstance(result, list):
                return result
            if isinstance(result, dict) and "questions" in result:
                return result["questions"]
    except Exception as e:
        logger.debug(f"Clinical inquiry failed: {e}")

    return _mock_clinical_questions(symptoms, preliminary_diseases)


async def _call_openai(prompt: str, json_mode: bool = True) -> dict:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
    )

    # Small / local models don't support response_format json_object
    use_json_mode = json_mode and not _is_ollama()

    kwargs: dict = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
    }

    # Limit tokens for small models
    if _is_ollama():
        kwargs["max_tokens"] = 1024
        kwargs["num_ctx"] = 2048   # Ollama-specific context window
    else:
        kwargs["max_tokens"] = 4000

    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    try:
        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        logger.info(f"LLM response ({len(content)} chars): {content[:200]}")
        return _extract_json(content)
    except Exception as e:
        logger.error(f"OpenAI/Ollama call failed: {e}")
        raise


async def _call_anthropic(prompt: str) -> dict:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=4000,
        system=DIAGNOSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt + "\nRespond with valid JSON only."}],
    )
    content = response.content[0].text
    return _extract_json(content)


def _mock_clinical_questions(symptoms: list[str], diseases: list[str]) -> list[dict]:
    sym_lower = " ".join(symptoms).lower()
    if any(w in sym_lower for w in ["aortic", "marfan", "tall", "pectus"]):
        return [
            {"question": "Family history of aortic aneurysm or sudden cardiac death?",
             "options": ["Yes", "No", "Unknown"], "hpo_if_yes": "HP:0004942"},
            {"question": "Aortic root Z-score on echocardiogram?",
             "options": ["Z-score >2", "Z-score 1-2", "Normal", "Not done"], "hpo_if_yes": "HP:0002616"},
            {"question": "Ocular findings (lens dislocation, severe myopia)?",
             "options": ["Yes", "No", "Unknown"], "hpo_if_yes": "HP:0001083"},
        ]
    if any(w in sym_lower for w in ["tremor", "hepatomegaly", "copper", "kayser"]):
        return [
            {"question": "Serum ceruloplasmin level?",
             "options": ["Low (<20 mg/dL)", "Normal", "Not tested"], "hpo_if_yes": "HP:0003124"},
            {"question": "Kayser-Fleischer rings on slit-lamp?",
             "options": ["Present", "Absent", "Not performed"], "hpo_if_yes": "HP:0002383"},
            {"question": "24-hour urine copper?",
             "options": [">100 µg/24h", "40-100 µg/24h", "<40 µg/24h", "Not done"],
             "hpo_if_yes": "HP:0003409"},
        ]
    return [
        {"question": "Age of symptom onset?",
         "options": ["Neonatal", "Childhood (<10y)", "Adolescence", "Adulthood"], "hpo_if_yes": ""},
        {"question": "Symptom progression?",
         "options": ["Progressive", "Stable", "Episodic"], "hpo_if_yes": ""},
        {"question": "Affected family members?",
         "options": ["Yes - parents", "Yes - siblings", "No", "Unknown"], "hpo_if_yes": "HP:0000007"},
    ]


def _calc_age(dob: str) -> str:
    if not dob:
        return "Unknown"
    try:
        from datetime import date
        birth = date.fromisoformat(dob)
        today = date.today()
        age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
        return f"{age} years"
    except Exception:
        return dob
