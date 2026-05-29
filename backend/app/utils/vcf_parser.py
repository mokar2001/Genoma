"""
VCF parser utility.
Currently extracts basic variant information from uploaded VCF files.
Phase 2: integrate with htslib / pysam for full GATK-compatible parsing.
"""

import re
from typing import List, Dict, Any


def parse_vcf(content: str) -> List[Dict[str, Any]]:
    """
    Parse a VCF file content string and return a list of variant dicts.
    Supports VCF 4.1 / 4.2 format.
    """
    variants = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue
        chrom, pos, vid, ref, alt = parts[0], parts[1], parts[2], parts[3], parts[4]
        info_str = parts[7] if len(parts) > 7 else ""
        info = _parse_info(info_str)

        variants.append(
            {
                "chromosome": chrom.replace("chr", ""),
                "position": int(pos),
                "variant_id": vid if vid != "." else f"{chrom}:{pos}:{ref}>{alt}",
                "ref": ref,
                "alt": alt,
                "gene": info.get("GENE", info.get("ANN_GENE", "UNKNOWN")),
                "gnomad_af": float(info.get("AF", info.get("gnomAD_AF", 0.0))),
                "info": info,
            }
        )
    return variants


def _parse_info(info_str: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    for field in info_str.split(";"):
        if "=" in field:
            k, v = field.split("=", 1)
            result[k] = v
        else:
            result[field] = "true"
    return result


def count_variants(content: str) -> int:
    return sum(
        1
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )
