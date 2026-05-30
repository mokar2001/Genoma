"""
LLM Service — configurable provider.
Supports OpenAI and Anthropic. Falls back to structured mock when no key set.
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

DIAGNOSIS_SYSTEM_PROMPT = """You are DeepRare, an expert AI system for rare disease diagnosis.
You have deep knowledge of 7,000+ rare diseases, their phenotypes, genetics, and molecular mechanisms.
Your task is to analyze patient information and provide ranked differential diagnoses with transparent,
evidence-based reasoning. Always cite specific HPO terms, OMIM IDs, and Orphanet codes when available.
Be precise, clinical, and traceable. Format your response as structured JSON."""


async def llm_diagnose(
    hpo_terms: list[dict],
    variants: list[dict],
    patient_meta: dict,
    pubcasefinder_results: list[dict],
    phenobrain_results: list[dict],
    suspected_diseases: list[str],
    memory_bank: dict,
) -> dict:
    """
    Central host LLM call — synthesizes all collected evidence into ranked diagnoses.
    Returns dict with candidates list and reasoning.
    """
    if settings.MOCK_MODE:
        return _mock_llm_response(hpo_terms, variants, suspected_diseases)

    prompt = _build_diagnosis_prompt(
        hpo_terms, variants, patient_meta,
        pubcasefinder_results, phenobrain_results, suspected_diseases, memory_bank,
    )

    if settings.OPENAI_API_KEY:
        return await _call_openai(prompt)
    elif settings.ANTHROPIC_API_KEY:
        return await _call_anthropic(prompt)

    return _mock_llm_response(hpo_terms, variants, suspected_diseases)


async def llm_self_reflect(
    candidates: list[dict],
    hpo_terms: list[dict],
    evidence: dict,
) -> dict:
    """
    Self-reflection step — validates or refutes each candidate diagnosis.
    Returns refined candidate list.
    """
    if settings.MOCK_MODE:
        return {"validated": candidates, "reflection_notes": "Mock validation — all candidates passed."}

    prompt = _build_reflection_prompt(candidates, hpo_terms, evidence)

    if settings.OPENAI_API_KEY:
        result = await _call_openai(prompt)
    elif settings.ANTHROPIC_API_KEY:
        result = await _call_anthropic(prompt)
    else:
        result = {"validated": candidates}

    return result


async def llm_extract_hpo(free_text: str) -> list[str]:
    """Extract HPO terms from free-text clinical description."""
    if settings.MOCK_MODE or (not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY):
        return []

    prompt = f"""Extract HPO phenotype terms from this clinical text. Return JSON array of strings.
Clinical text: {free_text}
Return: ["term1", "term2", ...]"""

    try:
        if settings.OPENAI_API_KEY:
            result = await _call_openai(prompt, json_mode=False)
            import json
            return json.loads(result.get("raw", "[]"))
    except Exception as e:
        logger.debug(f"HPO extraction failed: {e}")
    return []


async def llm_clinical_inquiry(
    patient_data: dict,
    symptoms: list[str],
    preliminary_diseases: list[str],
) -> list[dict]:
    """
    Stage 2: Generate targeted clinical follow-up questions to narrow diagnosis.
    Returns list of questions with options.
    """
    if settings.MOCK_MODE or (not settings.OPENAI_API_KEY and not settings.ANTHROPIC_API_KEY):
        return _mock_clinical_questions(symptoms, preliminary_diseases)

    prompt = f"""You are a rare disease specialist conducting a systematic clinical inquiry.
Patient symptoms: {', '.join(symptoms)}
Preliminary candidate diseases: {', '.join(preliminary_diseases[:3])}
Patient age: {patient_data.get('date_of_birth', 'unknown')}
Family history: {patient_data.get('familial_type', 'unknown')}

Generate 3-5 targeted clinical questions to narrow the differential diagnosis.
Return JSON array: [{{"question": "...", "options": ["Yes", "No", "Unknown"], "hpo_if_yes": "HP:XXXXXXX"}}]"""

    try:
        if settings.OPENAI_API_KEY:
            result = await _call_openai(prompt, json_mode=False)
            import json
            return json.loads(result.get("raw", "[]"))
        elif settings.ANTHROPIC_API_KEY:
            result = await _call_anthropic(prompt)
            return result.get("questions", _mock_clinical_questions(symptoms, preliminary_diseases))
    except Exception as e:
        logger.debug(f"Clinical inquiry failed: {e}")

    return _mock_clinical_questions(symptoms, preliminary_diseases)


def _build_diagnosis_prompt(hpo_terms, variants, patient_meta, pcf_results, pbr_results, suspected, memory) -> str:
    hpo_str = ", ".join([f"{t['name']} ({t['id']})" for t in hpo_terms if t.get("id")])
    var_str = ", ".join([f"{v.get('gene')} {v.get('cdna_change', '')}" for v in variants[:5]])
    pcf_str = ", ".join([r.get("disease_name_en", r.get("name", "")) for r in pcf_results[:5]])
    pbr_str = ", ".join([r.get("disease_name", "") for r in pbr_results[:5]])

    return f"""Analyze this rare disease case and provide top-5 differential diagnoses.

PATIENT INFORMATION:
- Age: {_calc_age(patient_meta.get('date_of_birth', ''))}
- Sex: {patient_meta.get('sex', 'Unknown')}
- Ethnicity: {patient_meta.get('ethnicity', 'Unknown')}
- Familial pattern: {patient_meta.get('familial_type', 'Unknown')}
- Consanguinity: {patient_meta.get('consanguinity', False)}

HPO PHENOTYPE TERMS: {hpo_str or 'None resolved'}
GENETIC VARIANTS: {var_str or 'None provided'}
SUSPECTED BY CLINICIAN: {', '.join(suspected) or 'None'}

BIOINFORMATICS TOOL RESULTS:
- PubCaseFinder: {pcf_str or 'No results'}
- PhenoBrain: {pbr_str or 'No results'}

RETRIEVED EVIDENCE:
{str(memory)[:2000] if memory else 'None'}

Provide top-5 rare disease diagnoses. For each, include:
1. Disease name (exact Orphanet name)
2. ORPHA code
3. OMIM ID
4. Confidence score (0-1)
5. Phenotype match score (0-1)
6. Genotype match score (0-1, 0 if no variants)
7. Matched HPO terms
8. Reasoning chain with evidence citations
9. Inheritance pattern
10. Prevalence

Return as JSON: {{"candidates": [{{...}}], "reasoning_summary": "..."}}"""


def _build_reflection_prompt(candidates, hpo_terms, evidence) -> str:
    return f"""Self-reflection: Validate or refute these candidate diagnoses for a rare disease patient.

HPO terms: {[t['name'] for t in hpo_terms]}
Candidates: {[c.get('disease_name') for c in candidates]}
Evidence: {str(evidence)[:1000]}

For each candidate, verify:
1. Are ALL key phenotype features explained?
2. Is the inheritance pattern consistent?
3. Is the gene-phenotype association established?
4. Rate confidence: high/medium/low

Remove candidates with confidence=low if better alternatives exist.
Return JSON: {{"validated": [{{...updated candidates...}}], "reflection_notes": "..."}}"""


def _mock_llm_response(hpo_terms, variants, suspected) -> dict:
    """Structured mock response matching LLM output format."""
    return {
        "candidates": [],
        "reasoning_summary": "Mock mode — configure OPENAI_API_KEY or ANTHROPIC_API_KEY for real LLM reasoning.",
    }


def _mock_clinical_questions(symptoms: list[str], diseases: list[str]) -> list[dict]:
    sym_lower = " ".join(symptoms).lower()
    questions = []

    if any(w in sym_lower for w in ["aortic", "marfan", "tall", "pectus"]):
        questions = [
            {"question": "Does the patient have a family history of aortic aneurysm or sudden cardiac death?", "options": ["Yes", "No", "Unknown"], "hpo_if_yes": "HP:0004942"},
            {"question": "Has an echocardiogram been performed? If so, what was the aortic root Z-score?", "options": ["Z-score >2", "Z-score 1-2", "Normal", "Not done"], "hpo_if_yes": "HP:0002616"},
            {"question": "Are there ocular findings? (Lens dislocation, severe myopia)", "options": ["Yes", "No", "Unknown"], "hpo_if_yes": "HP:0001083"},
        ]
    elif any(w in sym_lower for w in ["tremor", "hepatomegaly", "copper", "kayser"]):
        questions = [
            {"question": "What is the serum ceruloplasmin level?", "options": ["Low (<20 mg/dL)", "Normal", "Not tested"], "hpo_if_yes": "HP:0003124"},
            {"question": "Has a slit-lamp examination been performed for Kayser-Fleischer rings?", "options": ["Rings present", "Rings absent", "Not performed"], "hpo_if_yes": "HP:0002383"},
            {"question": "What is the 24-hour urine copper?", "options": [">100 µg/24h", "40-100 µg/24h", "<40 µg/24h", "Not done"], "hpo_if_yes": "HP:0003409"},
        ]
    else:
        questions = [
            {"question": "When did the symptoms first appear?", "options": ["Birth/Neonatal", "Childhood (<10y)", "Adolescence", "Adulthood"], "hpo_if_yes": ""},
            {"question": "Are symptoms progressive or stable?", "options": ["Progressive", "Stable", "Episodic/relapsing"], "hpo_if_yes": ""},
            {"question": "Are there any affected family members with similar symptoms?", "options": ["Yes - parents", "Yes - siblings", "Yes - extended family", "No"], "hpo_if_yes": "HP:0000007"},
        ]

    return questions


async def _call_openai(prompt: str, json_mode: bool = True) -> dict:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_BASE_URL if settings.OPENAI_BASE_URL else None,
    )

    kwargs: dict = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": DIAGNOSIS_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "max_tokens": 4000,
        "temperature": 0.1,
    }

    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    content = response.choices[0].message.content

    if json_mode:
        import json
        return json.loads(content)
    return {"raw": content}


async def _call_anthropic(prompt: str) -> dict:
    import anthropic
    import json

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=4000,
        system=DIAGNOSIS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt + "\nRespond with valid JSON only."}],
    )
    content = response.content[0].text
    try:
        return json.loads(content)
    except Exception:
        return {"raw": content, "candidates": []}


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
