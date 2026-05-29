from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


class PipelineStage(str, Enum):
    QUEUED = "queued"
    PARSING_VCF = "parsing_vcf"
    DEEPRARE = "deeprare"
    ACMG = "acmg"
    ALPHAFOLD = "alphafold"
    GENERATING_REPORT = "generating_report"
    COMPLETE = "complete"
    ERROR = "error"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    ERROR = "error"


class SSEEvent(BaseModel):
    stage: PipelineStage
    status: StageStatus
    progress: int  # 0-100
    message: str
    data: Optional[Dict[str, Any]] = None


# ─── DeepRare Results ─────────────────────────────────────────────────────────

class DiseaseCandidate(BaseModel):
    rank: int
    disease_name: str
    orpha_code: str
    omim_id: Optional[str] = None
    score: float                    # 0.0 – 1.0
    phenotype_match_score: float
    genotype_match_score: float
    prevalence: str
    inheritance_pattern: str
    matched_symptoms: List[str]
    unmatched_symptoms: List[str]
    supporting_genes: List[str]
    reasoning: str


class DeepRareResult(BaseModel):
    candidates: List[DiseaseCandidate]
    total_variants_analyzed: int
    phenotype_terms_matched: int
    model_version: str = "DeepRare-v2.1-mock"
    confidence_note: str


# ─── ACMG Results ─────────────────────────────────────────────────────────────

class ACMGClassification(str, Enum):
    PATHOGENIC = "Pathogenic"
    LIKELY_PATHOGENIC = "Likely Pathogenic"
    VUS = "Variant of Uncertain Significance"
    LIKELY_BENIGN = "Likely Benign"
    BENIGN = "Benign"


class ACMGCriterion(BaseModel):
    code: str          # e.g. PVS1, PS1, PM2
    met: bool
    strength: str      # Pathogenic_VeryStrong / Pathogenic_Strong / etc.
    description: str


class VariantResult(BaseModel):
    variant_id: str
    gene: str
    cdna_change: str
    protein_change: str
    chromosome: str
    position: int
    ref: str
    alt: str
    zygosity: str
    gnomad_af: float          # allele frequency
    classification: ACMGClassification
    classification_score: int  # net score
    criteria_met: List[ACMGCriterion]
    clinical_significance: str
    associated_diseases: List[str]
    actionable: bool
    recommendation: str


class ACMGResult(BaseModel):
    variants: List[VariantResult]
    pathogenic_count: int
    likely_pathogenic_count: int
    vus_count: int
    benign_count: int
    actionable_variants: List[str]
    classifier_version: str = "ACMG-2015-mock"


# ─── AlphaFold3 Results ───────────────────────────────────────────────────────

class ProteinStructure(BaseModel):
    gene: str
    uniprot_id: str
    pdb_id: Optional[str] = None
    structure_url: str             # URL or base64 PDB data
    plddt_score: float             # confidence 0-100
    variant_position: int
    wild_type_residue: str
    mutant_residue: str


class StructuralImpact(BaseModel):
    impact_type: str               # e.g. "Domain disruption", "Disulfide bond loss"
    severity: str                  # High / Medium / Low
    affected_domain: str
    description: str


class AlphaFoldResult(BaseModel):
    gene: str
    variant: str
    wild_type_structure: ProteinStructure
    mutant_structure: ProteinStructure
    rmsd: float                    # Å deviation between WT and mutant
    structural_impacts: List[StructuralImpact]
    pathogenicity_upgrade: bool    # did this upgrade a VUS?
    upgraded_from: Optional[str] = None
    upgraded_to: Optional[str] = None
    functional_summary: str
    pdb_wild_type: str             # inline PDB data for viewer
    pdb_mutant: str


# ─── Full Pipeline Result ─────────────────────────────────────────────────────

class PipelineResult(BaseModel):
    session_id: str
    patient_name: str
    deeprare: DeepRareResult
    acmg: ACMGResult
    alphafold: List[AlphaFoldResult]
    summary: str
    time_to_diagnosis_estimate: str
    report_url: Optional[str] = None
