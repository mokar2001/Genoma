"""
VCF Parser — supports VCF 4.1 / 4.2
Extracts variants with gene annotation from INFO field.
"""

import re
from pathlib import Path
from typing import Optional


def parse_vcf(content: str) -> list[dict]:
    variants = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 5:
            continue

        chrom = parts[0].replace("chr", "")
        pos   = int(parts[1])
        vid   = parts[2]
        ref   = parts[3]
        alt   = parts[4]
        info  = _parse_info(parts[7]) if len(parts) > 7 else {}

        gene = (
            info.get("GENE")
            or info.get("gene")
            or info.get("ANN_GENE")
            or _guess_gene_from_clinvar(info)
            or "UNKNOWN"
        )

        af = 0.0
        for af_key in ("AF", "gnomAD_AF", "gnomad_AF", "AF_popmax"):
            if af_key in info:
                try:
                    af = float(info[af_key].split(",")[0])
                    break
                except ValueError:
                    pass

        cdna    = info.get("HGVS_c", info.get("c_notation", ""))
        protein = info.get("HGVS_p", info.get("p_notation", ""))

        variants.append({
            "chromosome":      chrom,
            "position":        pos,
            "variant_id":      vid if vid != "." else f"{chrom}:{pos}:{ref}>{alt}",
            "ref":             ref,
            "alt":             alt,
            "gene":            gene,
            "gnomad_af":       af,
            "cdna_change":     cdna,
            "protein_change":  protein,
            "zygosity":        _parse_zygosity(parts),
            "info":            info,
        })

    return variants


def load_local_vcf(path: str) -> list[dict]:
    """Load a VCF from a local filesystem path."""
    p = Path(path)
    if not p.exists():
        return []
    return parse_vcf(p.read_text(encoding="utf-8", errors="replace"))


def count_variants(content: str) -> int:
    return sum(
        1 for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def _parse_info(info_str: str) -> dict:
    result: dict[str, str] = {}
    for field in info_str.split(";"):
        if "=" in field:
            k, v = field.split("=", 1)
            result[k.strip()] = v.strip()
        elif field.strip():
            result[field.strip()] = "true"
    return result


def _parse_zygosity(parts: list[str]) -> str:
    """Infer zygosity from FORMAT/SAMPLE columns."""
    if len(parts) < 10:
        return "Unknown"
    fmt    = parts[8].split(":")
    sample = parts[9].split(":")
    if "GT" not in fmt:
        return "Unknown"
    gt_idx = fmt.index("GT")
    if gt_idx >= len(sample):
        return "Unknown"
    gt = sample[gt_idx]
    alleles = re.split(r"[/|]", gt)
    if len(alleles) == 2:
        if alleles[0] == alleles[1] and alleles[0] != "0":
            return "Homozygous"
        if "0" in alleles:
            return "Heterozygous"
    return "Unknown"


def _guess_gene_from_clinvar(info: dict) -> Optional[str]:
    """Try to extract gene from ANN or CSQ fields (SnpEff / VEP annotation)."""
    ann = info.get("ANN") or info.get("CSQ", "")
    if ann:
        parts = ann.split("|")
        if len(parts) > 3:
            gene = parts[3].strip()
            if gene and gene != ".":
                return gene
    return None
