"""
VCF Parser — supports VCF 4.1 / 4.2 (plain or .gz).
Streams line-by-line and caps the number of variants so a whole-genome VCF
(millions of rows) never blows up memory or the JSON column.

For diagnostic use we prioritise variants that carry a gene annotation and/or
are rare, and cap the total kept.
"""

import re
import gzip
import io
import logging
from pathlib import Path
from typing import Optional, Iterator

logger = logging.getLogger(__name__)

# Hard cap on variants kept from a single VCF. WGS has millions; we only need
# the annotated / potentially-relevant subset for prioritisation.
MAX_VARIANTS = 20000


def _open_text(path: Path) -> Iterator[str]:
    """Yield lines from a plain or gzipped VCF without loading it all in RAM."""
    if path.suffix == ".gz" or path.name.endswith(".vcf.gz"):
        with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line
    else:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                yield line


def _parse_line(line: str) -> Optional[dict]:
    line = line.rstrip("\n")
    if not line or line.startswith("#"):
        return None
    parts = line.split("\t")
    if len(parts) < 5:
        return None

    chrom = parts[0].replace("chr", "")
    try:
        pos = int(parts[1])
    except ValueError:
        return None
    vid = parts[2]
    ref = parts[3]
    alt = parts[4]
    info = _parse_info(parts[7]) if len(parts) > 7 else {}

    gene = (
        info.get("GENE")
        or info.get("gene")
        or info.get("ANN_GENE")
        or _guess_gene_from_info(info)
        or "UNKNOWN"
    )

    af = 0.0
    for af_key in ("gnomAD_AF", "gnomad_AF", "AF_popmax", "AF"):
        if af_key in info:
            try:
                af = float(str(info[af_key]).split(",")[0])
                break
            except ValueError:
                pass

    return {
        "chromosome": chrom,
        "position": pos,
        "variant_id": vid if vid != "." else f"{chrom}:{pos}:{ref}>{alt}",
        "ref": ref,
        "alt": alt[:64],
        "gene": gene,
        "gnomad_af": af,
        "cdna_change": info.get("HGVS_c", info.get("c_notation", "")),
        "protein_change": info.get("HGVS_p", info.get("p_notation", "")),
        "consequence": info.get("Consequence", info.get("CLNVC", "")),
        "clnsig": info.get("CLNSIG", ""),
        "zygosity": _parse_zygosity(parts),
        # NOTE: the bulky raw INFO dict is intentionally NOT stored.
    }


def parse_vcf(content: str, max_variants: int = MAX_VARIANTS) -> list[dict]:
    """Parse VCF text content (small files / in-memory)."""
    variants: list[dict] = []
    annotated: list[dict] = []
    for line in content.splitlines():
        v = _parse_line(line)
        if v is None:
            continue
        # Prefer annotated variants (named gene or clinical significance)
        if v["gene"] != "UNKNOWN" or v["clnsig"]:
            annotated.append(v)
        elif len(variants) < max_variants:
            variants.append(v)
        if len(annotated) >= max_variants:
            break
    combined = (annotated + variants)[:max_variants]
    return combined


def load_local_vcf(path: str, max_variants: int = MAX_VARIANTS) -> list[dict]:
    """
    Stream a VCF from disk (plain or .gz), keeping at most `max_variants`.
    Annotated / clinically-significant variants are prioritised.
    """
    p = Path(path)
    if not p.exists():
        logger.warning(f"VCF not found: {path}")
        return []

    annotated: list[dict] = []
    plain: list[dict] = []
    scanned = 0

    try:
        for line in _open_text(p):
            v = _parse_line(line)
            if v is None:
                continue
            scanned += 1
            if v["gene"] != "UNKNOWN" or v["clnsig"]:
                if len(annotated) < max_variants:
                    annotated.append(v)
            elif len(plain) < max_variants:
                plain.append(v)
            # Stop early: enough annotated, or enough total kept (caps WGS scan)
            if len(annotated) >= max_variants:
                break
            if len(annotated) + len(plain) >= max_variants:
                break
    except Exception as e:
        logger.warning(f"VCF parse error for {path}: {e}")

    combined = (annotated + plain)[:max_variants]
    logger.info(
        f"Parsed VCF {p.name}: scanned≈{scanned}, kept {len(combined)} "
        f"({len(annotated)} annotated)"
    )
    return combined


def count_variants(content: str) -> int:
    return sum(
        1 for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def _parse_info(info_str: str) -> dict:
    result: dict[str, str] = {}
    for field in info_str.split(";"):
        if "=" in field:
            k, _, v = field.partition("=")
            result[k] = v
    return result


def _parse_zygosity(parts: list[str]) -> str:
    if len(parts) < 10:
        return "Unknown"
    fmt = parts[8].split(":")
    if "GT" not in fmt:
        return "Unknown"
    gt = parts[9].split(":")[fmt.index("GT")]
    alleles = re.split(r"[/|]", gt)
    if len(alleles) == 2:
        if alleles[0] == alleles[1] and alleles[0] not in ("0", "."):
            return "Homozygous"
        if "0" in alleles:
            return "Heterozygous"
    return "Unknown"


def _guess_gene_from_info(info: dict) -> Optional[str]:
    # ClinVar: GENEINFO=BRCA1:672
    gi = info.get("GENEINFO", "")
    if gi:
        return gi.split(":")[0]
    # SnpEff ANN / VEP CSQ
    ann = info.get("ANN") or info.get("CSQ", "")
    if ann:
        fields = ann.split("|")
        if len(fields) > 3 and fields[3].strip() and fields[3] != ".":
            return fields[3].strip()
    return None
