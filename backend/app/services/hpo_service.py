"""
HPO Service — Phenotype Extractor Agent
========================================
Converts free-text symptoms to standardized HPO terms using:
  1. BioLORD cosine similarity (when embeddings ready) — paper method
  2. Local curated map (fast offline fallback)
  3. HPO JAX search API (online fallback)

This implements the aHPO agent server from the DeepRare paper.
"""

import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Local curated map (fast path, no network/GPU needed) ─────────────────────
LOCAL_HPO_MAP: dict[str, str] = {
    # Cardiovascular / autonomic
    "hypertension": "HP:0000822",
    "arterial hypertension": "HP:0000822",
    "high blood pressure": "HP:0000822",
    "hypotension": "HP:0002615",
    "tachycardia": "HP:0001649",
    "bradycardia": "HP:0001662",
    "palpitations": "HP:0001962",
    # Autonomic / skin
    "hyperhidrosis": "HP:0000970",
    "excessive sweating": "HP:0000970",
    "diaphoresis": "HP:0000970",
    "anhidrosis": "HP:0000966",
    "flushing": "HP:0001310",
    "raynaud phenomenon": "HP:0100576",
    # Immune / allergy
    "hypersensitivity": "HP:0002099",
    "allergic reaction": "HP:0012393",
    "anaphylaxis": "HP:0002197",
    "urticaria": "HP:0001025",
    "angioedema": "HP:0100665",
    "eczema": "HP:0000964",
    "autoimmunity": "HP:0002960",
    # General
    "fatigue": "HP:0012378",
    "chronic fatigue": "HP:0012378",
    "weight loss": "HP:0001824",
    "weight gain": "HP:0004324",
    "fever": "HP:0001945",
    "recurrent fever": "HP:0001954",
    "pain": "HP:0012531",
    "headache": "HP:0002315",
    "migraine": "HP:0002076",
    "nausea": "HP:0002018",
    "vomiting": "HP:0002013",
    "diarrhea": "HP:0002014",
    "constipation": "HP:0002019",
    # Marfan / connective tissue
    "arachnodactyly": "HP:0001166",
    "pectus excavatum": "HP:0000767",
    "pectus carinatum": "HP:0000768",
    "ectopia lentis": "HP:0001083",
    "aortic root dilation": "HP:0002616",
    "aortic aneurysm": "HP:0004942",
    "scoliosis": "HP:0002650",
    "tall stature": "HP:0000098",
    "hypermobility": "HP:0001382",
    "joint hypermobility": "HP:0001382",
    "lens dislocation": "HP:0001083",
    "myopia": "HP:0000545",
    "mitral valve prolapse": "HP:0001634",
    # Neurological
    "seizures": "HP:0001250",
    "intellectual disability": "HP:0001249",
    "hypotonia": "HP:0001252",
    "ataxia": "HP:0001251",
    "tremor": "HP:0001337",
    "dysarthria": "HP:0001260",
    "spasticity": "HP:0001257",
    "nystagmus": "HP:0000639",
    "microcephaly": "HP:0000252",
    "macrocephaly": "HP:0000256",
    "behavioral changes": "HP:0000708",
    "developmental delay": "HP:0001263",
    "regression": "HP:0002376",
    # Ophthalmologic
    "cataracts": "HP:0000518",
    "glaucoma": "HP:0000501",
    "retinal dystrophy": "HP:0000556",
    "ptosis": "HP:0000508",
    "strabismus": "HP:0000486",
    "kayser-fleischer rings": "HP:0002383",
    "corneal clouding": "HP:0007957",
    # Hepatic / metabolic
    "hepatomegaly": "HP:0002240",
    "splenomegaly": "HP:0001744",
    "hepatosplenomegaly": "HP:0001433",
    "cirrhosis": "HP:0001394",
    "jaundice": "HP:0000952",
    "elevated liver enzymes": "HP:0002910",
    "elevated serum copper": "HP:0003409",
    "low ceruloplasmin": "HP:0003124",
    "hyperammonemia": "HP:0001987",
    "metabolic acidosis": "HP:0001942",
    # Hematologic
    "anemia": "HP:0001903",
    "thrombocytopenia": "HP:0001873",
    "lymphadenopathy": "HP:0002716",
    "axillary lymphadenopathy": "HP:0007667",
    "pancytopenia": "HP:0001876",
    # Cardiac
    "cardiomyopathy": "HP:0001638",
    "arrhythmia": "HP:0011675",
    "heart failure": "HP:0001635",
    "ventricular hypertrophy": "HP:0001714",
    "congenital heart defect": "HP:0001627",
    # Skeletal / dysmorphic
    "short stature": "HP:0004322",
    "polydactyly": "HP:0010442",
    "syndactyly": "HP:0001159",
    "cleft palate": "HP:0000175",
    "clinodactyly": "HP:0030084",
    "clubfoot": "HP:0001762",
    "kyphosis": "HP:0002808",
    "lordosis": "HP:0003307",
    "genu valgum": "HP:0002857",
    # Renal
    "renal cysts": "HP:0000107",
    "proteinuria": "HP:0000093",
    "nephropathy": "HP:0000112",
    "hematuria": "HP:0000790",
    "renal failure": "HP:0000083",
    # Skin / hair
    "ichthyosis": "HP:0008064",
    "sparse hair": "HP:0008070",
    "hypopigmentation": "HP:0001010",
    "cafe-au-lait spots": "HP:0000957",
    "angiofibromas": "HP:0010610",
    "telangiectasia": "HP:0001009",
    # Oncology
    "breast lump": "HP:0031093",
    "family history of early-onset breast cancer": "HP:0003002",
    "elevated ca 15-3": "HP:0030358",
    # Respiratory
    "recurrent respiratory infections": "HP:0002205",
    "bronchiectasis": "HP:0002088",
    "dyspnea": "HP:0002094",
    # Endocrine
    "diabetes insipidus": "HP:0000873",
    "hypothyroidism": "HP:0000821",
    "hyperthyroidism": "HP:0000840",
    "adrenal insufficiency": "HP:0000846",
    "precocious puberty": "HP:0000826",
}


async def symptoms_to_hpo(symptoms: list[str]) -> list[dict]:
    """
    Convert symptom strings to HPO term objects.
    Pipeline (per DeepRare paper):
      1. BioLORD cosine similarity (if embeddings ready)
      2. Local curated map
      3. HPO JAX search API

    Returns list of {id, name, original_symptom, score, source}
    """
    results = []
    seen_ids: set[str] = set()

    for symptom in symptoms:
        hpo = await _resolve_single(symptom)
        if hpo and hpo["id"] and hpo["id"] not in seen_ids:
            seen_ids.add(hpo["id"])
            results.append(hpo)
        elif hpo and not hpo["id"]:
            # Keep as free-text term (no HPO ID resolved)
            results.append(hpo)

    return results


async def _resolve_single(symptom: str) -> Optional[dict]:
    key = symptom.strip().lower()

    # 1. BioLORD cosine similarity (most accurate — paper method)
    try:
        from app.services.hpo_ontology import normalize_symptom_to_hpo, is_ready
        if is_ready():
            match = normalize_symptom_to_hpo(symptom, threshold=0.75)
            if match:
                return {
                    "id": match["id"],
                    "name": match["name"],
                    "original_symptom": symptom,
                    "score": match["score"],
                    "source": "biolord_cosine",
                }
    except Exception as e:
        logger.debug(f"BioLORD lookup failed for '{symptom}': {e}")

    # 2. Local curated map (fast, offline)
    if key in LOCAL_HPO_MAP:
        return {
            "id": LOCAL_HPO_MAP[key],
            "name": symptom,
            "original_symptom": symptom,
            "score": 1.0,
            "source": "local_map",
        }

    # Partial match in local map
    for map_key, hpo_id in LOCAL_HPO_MAP.items():
        if map_key in key or key in map_key:
            return {
                "id": hpo_id,
                "name": map_key,
                "original_symptom": symptom,
                "score": 0.85,
                "source": "local_map_partial",
            }

    # 3. HPO JAX search API
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://hpo.jax.org/api/hpo/search",
                params={"q": symptom, "max": 1, "category": "terms"},
            )
            if resp.status_code == 200:
                terms = resp.json().get("terms", [])
                if terms:
                    t = terms[0]
                    return {
                        "id": t.get("id", ""),
                        "name": t.get("name", symptom),
                        "original_symptom": symptom,
                        "score": 0.80,
                        "source": "hpo_api",
                    }
    except Exception as e:
        logger.debug(f"HPO API miss for '{symptom}': {e}")

    # 4. Return as unresolved free text
    return {
        "id": "",
        "name": symptom,
        "original_symptom": symptom,
        "score": 0.0,
        "source": "free_text",
    }
