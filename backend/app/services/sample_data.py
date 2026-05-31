"""
Sample VCF resolver
===================
When a user ticks "Use sample VCF (mock run)", we analyse a real VCF stored
on the server instead of an uploaded file.

Drop sample VCFs here on the server (host path):
    ~/Genoma/backend/demo_data/

They are visible inside the container at:
    /app/demo_data/

Priority:
  1. SAMPLE_VCF_PATH env var (explicit override)
  2. A symptom-matched demo VCF (marfan / brca1 / wilson)
  3. The generic default: /app/demo_data/sample.vcf
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEMO_DIR = Path("/app/demo_data")


def _symptom_match(symptoms: list[str]) -> str:
    s = " ".join(symptoms).lower()
    if any(w in s for w in ["aortic", "marfan", "pectus", "arachnodactyly",
                            "scoliosis", "tall stature", "ectopia"]):
        return "sample_marfan.vcf"
    if any(w in s for w in ["breast", "brca", "ovarian", "axillary"]):
        return "sample_brca1.vcf"
    if any(w in s for w in ["copper", "wilson", "kayser", "ceruloplasmin",
                            "hepatomegaly", "tremor", "dysarthria"]):
        return "sample_wilson.vcf"
    return ""


def resolve_sample_vcf(symptoms: list[str] | None = None) -> str:
    """Return an absolute path (inside the container) to a sample VCF that exists."""
    symptoms = symptoms or []

    # 1. Explicit override
    override = os.getenv("SAMPLE_VCF_PATH", "")
    if override and Path(override).exists():
        return override

    # 2. Symptom-matched demo file
    match = _symptom_match(symptoms)
    if match:
        p = DEMO_DIR / match
        if p.exists():
            return str(p)

    # 3. Generic default
    default = DEMO_DIR / "sample.vcf"
    if default.exists():
        return str(default)

    # 4. Any VCF in the demo dir
    if DEMO_DIR.exists():
        for f in DEMO_DIR.iterdir():
            if f.suffix in (".vcf",) or f.name.endswith(".vcf.gz"):
                return str(f)

    logger.warning("No sample VCF found in /app/demo_data — falling back to symptom-only")
    return ""
