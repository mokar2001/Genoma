"""
AlphaFold3 Structure Service — Phase 1: realistic mock.
Phase 2: call EBI AlphaFold API for WT + submit mutant to AF3 server.
"""

import asyncio
from typing import List, Dict, Any

from app.core.config import settings
from app.core.mock_data import MOCK_PDB_URLS
from app.models.pipeline import (
    AlphaFoldResult,
    ProteinStructure,
    StructuralImpact,
    ACMGClassification,
)


GENE_META = {
    "FBN1": {
        "uniprot": "P35555",
        "pdb_id": "7LTF",
        "domain": "Calcium-binding EGF-like domain 23",
        "wt_residue": "Arg",
        "mut_residue": "Cys",
        "position": 1155,
        "plddt_wt": 87.2,
        "plddt_mut": 71.4,
        "rmsd": 3.8,
        "impacts": [
            StructuralImpact(
                impact_type="Disulfide bond disruption",
                severity="High",
                affected_domain="cbEGF domain 23",
                description=(
                    "p.Arg1155Cys introduces a free cysteine that disrupts the canonical "
                    "disulfide bonding pattern in the cbEGF domain, destabilizing calcium coordination "
                    "critical for domain-domain interactions along the fibrillin-1 rod."
                ),
            ),
            StructuralImpact(
                impact_type="Domain folding instability",
                severity="High",
                affected_domain="cbEGF domain 23–24 interface",
                description=(
                    "Loss of electrostatic contact between Arg1155 and Asp1158 causes partial "
                    "unfolding of the cbEGF23-24 tandem, reducing the mechanical stiffness of "
                    "microfibrils in the extracellular matrix."
                ),
            ),
        ],
    },
    "BRCA1": {
        "uniprot": "P38398",
        "pdb_id": None,
        "domain": "BRCT domain",
        "wt_residue": "Gln",
        "mut_residue": "ProfsTer25",
        "position": 1756,
        "plddt_wt": 78.1,
        "plddt_mut": 44.3,
        "rmsd": 9.2,
        "impacts": [
            StructuralImpact(
                impact_type="Premature termination / truncation",
                severity="High",
                affected_domain="BRCT tandem repeat domain",
                description=(
                    "Frameshift at p.Gln1756 causes premature stop at +25 codons, "
                    "truncating the C-terminal BRCT domain entirely. "
                    "The BRCT domain is essential for phosphopeptide binding in DNA damage response."
                ),
            ),
            StructuralImpact(
                impact_type="Nonsense-mediated decay (NMD) target",
                severity="High",
                affected_domain="Full-length transcript",
                description=(
                    "Truncated mRNA is predicted to be degraded via NMD, resulting in "
                    "haploinsufficiency of BRCA1 — a well-established cancer predisposition mechanism."
                ),
            ),
        ],
    },
    "ATP7B": {
        "uniprot": "P35670",
        "pdb_id": None,
        "domain": "ATP-binding domain (ATPBD)",
        "wt_residue": "His",
        "mut_residue": "Gln",
        "position": 1069,
        "plddt_wt": 83.7,
        "plddt_mut": 68.9,
        "rmsd": 2.9,
        "impacts": [
            StructuralImpact(
                impact_type="ATP-binding site disruption",
                severity="High",
                affected_domain="ATPBD phosphorylation loop",
                description=(
                    "His1069 forms a critical hydrogen bond network in the ATP-binding pocket. "
                    "p.His1069Gln eliminates the imidazole side chain, collapsing the phosphorylation "
                    "loop and abolishing ATPase activity required for copper export."
                ),
            ),
            StructuralImpact(
                impact_type="Protein misfolding / ER retention",
                severity="Medium",
                affected_domain="Transmembrane domain 6",
                description=(
                    "Misfolded ATPBD triggers endoplasmic reticulum retention of ATP7B, "
                    "preventing trafficking to the trans-Golgi network — the site of copper "
                    "incorporation into ceruloplasmin."
                ),
            ),
        ],
    },
}


async def run_alphafold(
    actionable_variants: List[Dict[str, Any]],
    acmg_variants: List[Any],
) -> List[AlphaFoldResult]:
    await asyncio.sleep(settings.ALPHAFOLD_MOCK_DELAY)

    results = []
    seen_genes = set()

    for variant in actionable_variants:
        gene = variant.get("gene", "UNKNOWN")
        if gene in seen_genes or gene not in GENE_META:
            continue
        seen_genes.add(gene)

        meta = GENE_META[gene]
        wt_url = MOCK_PDB_URLS.get(f"{gene}_WT", "https://files.rcsb.org/download/1UBQ.pdb")

        # Check if this variant upgrades a VUS
        acmg_match = next(
            (v for v in acmg_variants if v.gene == gene), None
        )
        is_upgrade = acmg_match and acmg_match.classification == "Variant of Uncertain Significance"

        results.append(
            AlphaFoldResult(
                gene=gene,
                variant=variant.get("cdna_change", "c.?"),
                wild_type_structure=ProteinStructure(
                    gene=gene,
                    uniprot_id=meta["uniprot"],
                    pdb_id=meta["pdb_id"],
                    structure_url=wt_url,
                    plddt_score=meta["plddt_wt"],
                    variant_position=meta["position"],
                    wild_type_residue=meta["wt_residue"],
                    mutant_residue=meta["mut_residue"],
                ),
                mutant_structure=ProteinStructure(
                    gene=gene,
                    uniprot_id=meta["uniprot"],
                    pdb_id=None,
                    structure_url=wt_url,  # Phase 2: submit mutant sequence to AF3
                    plddt_score=meta["plddt_mut"],
                    variant_position=meta["position"],
                    wild_type_residue=meta["wt_residue"],
                    mutant_residue=meta["mut_residue"],
                ),
                rmsd=meta["rmsd"],
                structural_impacts=meta["impacts"],
                pathogenicity_upgrade=is_upgrade,
                upgraded_from=ACMGClassification.VUS if is_upgrade else None,
                upgraded_to=ACMGClassification.LIKELY_PATHOGENIC if is_upgrade else None,
                functional_summary=(
                    f"The {variant.get('protein_change', 'variant')} substitution in {gene} "
                    f"causes an RMSD of {meta['rmsd']}Å vs. wild-type, with plDDT dropping from "
                    f"{meta['plddt_wt']} to {meta['plddt_mut']}. "
                    f"Primary impact: {meta['impacts'][0].impact_type} in the {meta['domain']}."
                ),
                pdb_wild_type=wt_url,
                pdb_mutant=wt_url,  # Phase 2: actual mutant PDB
            )
        )

    return results
