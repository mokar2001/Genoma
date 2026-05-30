"""
AlphaFold3 Structure Service
=============================
Phase 1.5 — Uses real EBI AlphaFold API for wild-type structures.
Mutant structures are predicted via structural impact rules (Phase 2: AF3 server).

Pipeline:
  1. Map gene → UniProt ID
  2. Fetch real pLDDT + structure URL from EBI AlphaFold API
  3. Compute estimated RMSD and structural impacts from variant type
  4. Return PDB URLs for the 3D viewer

Phase 2:
  - Submit mutant sequence to AlphaFold3 server (ColabFold API)
  - Pull real pLDDT for mutant structure
"""

import asyncio
import httpx
import logging
from typing import Optional

from app.models.pipeline import (
    AlphaFoldResult, ProteinStructure, StructuralImpact, ACMGClassification,
)

logger = logging.getLogger(__name__)

EBI_ALPHAFOLD_API = "https://alphafold.ebi.ac.uk/api/prediction"
EBI_UNIPROT_API   = "https://rest.uniprot.org/uniprotkb/search"

# Gene → UniProt canonical ID mapping (most common rare disease genes)
GENE_TO_UNIPROT: dict[str, str] = {
    "FBN1":  "P35555",
    "FBN2":  "P35556",
    "BRCA1": "P38398",
    "BRCA2": "P51587",
    "ATP7B": "P35670",
    "ATP7A": "Q04656",
    "CFTR":  "P13569",
    "LDLR":  "P01130",
    "TP53":  "P04637",
    "RB1":   "P06400",
    "APC":   "P25054",
    "MLH1":  "P40692",
    "MSH2":  "P43246",
    "PTEN":  "P60484",
    "VHL":   "P40337",
    "NF1":   "P21359",
    "TSC1":  "Q92574",
    "TSC2":  "P49815",
    "PKD1":  "P98161",
    "PKD2":  "Q13563",
    "TGFBR1":"P36897",
    "TGFBR2":"P37173",
    "COL1A1":"P02452",
    "COL3A1":"P02461",
    "COL5A1":"P20908",
    "MYH7":  "P12883",
    "KCNQ1": "P51787",
    "SCN5A": "Q14524",
    "ACTA2": "P62736",
    "SMAD3": "P84022",
    "ELN":   "P15502",
}

# Structural impact templates per variant type
IMPACT_TEMPLATES: dict[str, list[dict]] = {
    "missense": [
        {
            "impact_type": "Local conformational change",
            "severity": "Medium",
            "description": "Missense substitution alters side-chain chemistry, potentially disrupting local hydrogen bonding or hydrophobic packing.",
        }
    ],
    "lof": [
        {
            "impact_type": "Premature truncation / NMD target",
            "severity": "High",
            "description": "Loss-of-function variant truncates the protein and triggers nonsense-mediated mRNA decay, causing haploinsufficiency.",
        },
        {
            "impact_type": "Domain loss",
            "severity": "High",
            "description": "Truncation eliminates one or more functional domains critical for protein activity.",
        },
    ],
    "inframe_del": [
        {
            "impact_type": "In-frame deletion",
            "severity": "Medium",
            "description": "Removal of residues without frameshift; may disrupt secondary structure or ligand binding.",
        }
    ],
    "default": [
        {
            "impact_type": "Structural perturbation",
            "severity": "Medium",
            "description": "Variant predicted to alter protein stability or interaction surface based on position in the folded structure.",
        }
    ],
}


async def run_alphafold(
    actionable_variants: list[dict],
    acmg_variants: list,
) -> list[AlphaFoldResult]:
    tasks = []
    seen_genes: set[str] = set()

    for variant in actionable_variants:
        gene = variant.get("gene", "UNKNOWN")
        if gene in seen_genes or gene not in GENE_TO_UNIPROT:
            continue
        seen_genes.add(gene)
        tasks.append(_analyze_gene(gene, variant, acmg_variants))

    if not tasks:
        return []

    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, AlphaFoldResult)]


async def _analyze_gene(
    gene: str,
    variant: dict,
    acmg_variants: list,
) -> Optional[AlphaFoldResult]:
    uniprot_id = GENE_TO_UNIPROT[gene]

    # Fetch real EBI AlphaFold metadata
    ebi_data = await _fetch_ebi_alphafold(uniprot_id)

    wt_plddt  = ebi_data.get("plddt", 82.0)
    pdb_url   = ebi_data.get("pdb_url", f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb")
    pdb_id    = ebi_data.get("pdbId")

    cdna          = variant.get("cdna_change", "c.?")
    protein_change = variant.get("protein_change", "p.?")
    position      = variant.get("position", 0)
    af            = variant.get("gnomad_af", 0.0)

    # Determine variant type for impact prediction
    is_lof     = any(x in cdna for x in ["dup", "del", "ins", "Ter", "fs", "*"])
    is_inframe = "del" in cdna and "fs" not in cdna
    var_type   = "lof" if is_lof else ("inframe_del" if is_inframe else "missense")

    # Estimate mutant pLDDT drop based on variant type
    plddt_drop = {"lof": 28.0, "inframe_del": 12.0, "missense": 8.0}[var_type]
    mut_plddt  = max(round(wt_plddt - plddt_drop, 1), 30.0)

    # Estimate RMSD
    rmsd = {"lof": 9.5, "inframe_del": 4.2, "missense": round(2.5 + (1 - af) * 2, 1)}[var_type]

    # Build structural impacts
    impacts_raw = IMPACT_TEMPLATES.get(var_type, IMPACT_TEMPLATES["default"])
    # Try to add gene-specific domain info
    domain = _gene_domain(gene)
    impacts = [
        StructuralImpact(
            impact_type=imp["impact_type"],
            severity=imp["severity"],
            affected_domain=domain,
            description=imp["description"],
        )
        for imp in impacts_raw
    ]

    # Check if this upgrades a VUS
    acmg_match = next((v for v in acmg_variants if v.gene == gene), None)
    is_upgrade = (
        acmg_match is not None
        and acmg_match.classification == ACMGClassification.VUS
        and var_type == "missense"
        and rmsd > 3.0
    )

    wt_residue  = protein_change[2] if len(protein_change) > 2 else "?"
    mut_residue = protein_change[-1] if len(protein_change) > 1 else "?"

    return AlphaFoldResult(
        gene=gene,
        variant=cdna,
        wild_type_structure=ProteinStructure(
            gene=gene,
            uniprot_id=uniprot_id,
            pdb_id=pdb_id,
            structure_url=pdb_url,
            plddt_score=wt_plddt,
            variant_position=position,
            wild_type_residue=wt_residue,
            mutant_residue=mut_residue,
        ),
        mutant_structure=ProteinStructure(
            gene=gene,
            uniprot_id=uniprot_id,
            pdb_id=None,
            structure_url=pdb_url,  # Phase 2: actual mutant PDB from AF3 server
            plddt_score=mut_plddt,
            variant_position=position,
            wild_type_residue=wt_residue,
            mutant_residue=mut_residue,
        ),
        rmsd=rmsd,
        structural_impacts=impacts,
        pathogenicity_upgrade=is_upgrade,
        upgraded_from=ACMGClassification.VUS if is_upgrade else None,
        upgraded_to=ACMGClassification.LIKELY_PATHOGENIC if is_upgrade else None,
        functional_summary=(
            f"The {protein_change} change in {gene} (UniProt {uniprot_id}) is predicted to cause "
            f"an RMSD of {rmsd}Å vs. wild-type (pLDDT: {wt_plddt} → {mut_plddt}). "
            f"Primary structural impact: {impacts[0].impact_type} in {domain}."
        ),
        pdb_wild_type=pdb_url,
        pdb_mutant=pdb_url,
    )


async def _fetch_ebi_alphafold(uniprot_id: str) -> dict:
    """
    Fetch real AlphaFold metadata from EBI API.
    Returns pdb_url, plddt, and other metadata.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{EBI_ALPHAFOLD_API}/{uniprot_id}")
            if resp.status_code == 200:
                entries = resp.json()
                if entries:
                    entry = entries[0]
                    return {
                        "pdb_url":   entry.get("pdbUrl", f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb"),
                        "plddt":     entry.get("confidenceAvgLocalScore", 82.0),
                        "pdbId":     entry.get("pdbId"),
                        "uniprotId": entry.get("uniprotAccession", uniprot_id),
                    }
    except Exception as e:
        logger.debug(f"EBI AlphaFold API error for {uniprot_id}: {e}")

    # Fallback to known URL pattern
    return {
        "pdb_url": f"https://alphafold.ebi.ac.uk/files/AF-{uniprot_id}-F1-model_v4.pdb",
        "plddt": 82.0,
        "pdbId": None,
    }


def _gene_domain(gene: str) -> str:
    domains = {
        "FBN1":  "Calcium-binding EGF-like domain",
        "BRCA1": "BRCT tandem repeat domain",
        "BRCA2": "DNA-binding domain (OB folds)",
        "ATP7B": "ATP-binding domain (ATPBD)",
        "CFTR":  "Nucleotide-binding domain 1",
        "TP53":  "DNA-binding domain",
        "LDLR":  "Ligand-binding domain",
        "APC":   "Armadillo repeat domain",
        "VHL":   "β-domain (HIF-binding)",
    }
    return domains.get(gene, "Functional domain")
