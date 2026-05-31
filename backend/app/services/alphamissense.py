"""
AlphaMissense lookup
====================
Queries the AlphaMissense pathogenicity table for a variant's
(chrom, pos, ref, alt) -> {am_score, am_class}.

The AlphaMissense_hg38.tsv.gz file is large (~1GB). We use tabix random-access
(pysam) so we never load it into memory. Download + index at setup:

  wget https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz
  tabix -s 1 -b 2 -e 2 -S 1 AlphaMissense_hg38.tsv.gz   # after bgzip if needed

If the file/index is absent, lookups return None (gracefully degraded).
"""

import logging
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_tabix = None
_checked = False


def _get_tabix():
    global _tabix, _checked
    if _checked:
        return _tabix
    _checked = True
    path = settings.ALPHAMISSENSE_TSV
    if not Path(path).exists():
        logger.info(f"AlphaMissense file not found at {path} — scores unavailable")
        return None
    try:
        import pysam
        _tabix = pysam.TabixFile(path)
        logger.info("AlphaMissense tabix loaded")
    except Exception as e:
        logger.warning(f"Could not open AlphaMissense tabix: {e}")
        _tabix = None
    return _tabix


def lookup(chrom: str, pos: int, ref: str, alt: str) -> Optional[dict]:
    """
    Return {am_pathogenicity, am_class} for a variant, or None.
    AlphaMissense columns: CHROM POS REF ALT genome uniprot transcript
                           protein_variant am_pathogenicity am_class
    """
    tb = _get_tabix()
    if tb is None:
        return None

    chrom_norm = chrom if chrom.startswith("chr") else f"chr{chrom}"
    try:
        for row in tb.fetch(chrom_norm, pos - 1, pos):
            cols = row.split("\t")
            if len(cols) < 10:
                continue
            r_ref, r_alt = cols[2], cols[3]
            if r_ref == ref and r_alt == alt:
                return {
                    "am_pathogenicity": float(cols[8]),
                    "am_class": cols[9],   # likely_benign | ambiguous | likely_pathogenic
                    "protein_variant": cols[7],
                }
    except Exception as e:
        logger.debug(f"AlphaMissense lookup failed {chrom}:{pos}: {e}")
    return None


def is_available() -> bool:
    return _get_tabix() is not None
