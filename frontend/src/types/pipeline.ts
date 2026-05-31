export type PipelineStage =
  | "queued"
  | "sequencing"
  | "parsing_vcf"
  | "phenotype"
  | "similarity"
  | "literature"
  | "prioritization"
  | "structure"
  | "diagnosis"
  | "complete"
  | "error";

export type StageStatus = "pending" | "running" | "complete" | "error";

export interface SSEEvent {
  stage: PipelineStage;
  status: StageStatus;
  progress: number;
  message: string;
  data?: Record<string, unknown>;
}

export interface PhenotypeTerm {
  term: string;
  original: string;
  hpo_id: string;
  source: string;
  score: number;
}

export interface SimilarCase {
  disease: string;
  score: number;
  source: string;
  gene: string;
  orpha_code: string;
  omim_id: string;
  hpo_overlap: string[];
  overlap_count: number;
}

export interface LiteratureItem {
  title: string;
  authors: string;
  journal: string;
  year: string;
  pmid: string;
  doi: string;
  url: string;
  snippet: string;
  citations: number;
  source: string;
}

export interface PrioritizedVariant {
  gene: string;
  variant_id?: string;
  cdna_change: string;
  protein_change: string;
  chromosome: string;
  position: number;
  ref: string;
  alt: string;
  zygosity: string;
  gnomad_af: number;
  consequence: string;
  clinvar_significance: string;
  franklin?: string | null;
  alphamissense?: { am_pathogenicity: number; am_class: string } | null;
  is_lof: boolean;
  is_missense: boolean;
  gene_phenotype_match: boolean;
  priority_score: number;
  priority_reasons: string[];
  novel: boolean;
}

export type ACMGClassification =
  | "Pathogenic"
  | "Likely Pathogenic"
  | "Variant of Uncertain Significance"
  | "Likely Benign"
  | "Benign";

export interface ACMGCriterion {
  code: string;
  met: boolean;
  strength: string;
  description: string;
}

export interface VariantResult {
  variant_id: string;
  gene: string;
  cdna_change: string;
  protein_change: string;
  chromosome: string;
  position: number;
  ref: string;
  alt: string;
  zygosity: string;
  gnomad_af: number;
  classification: ACMGClassification;
  classification_score: number;
  criteria_met: ACMGCriterion[];
  clinical_significance: string;
  associated_diseases: string[];
  actionable: boolean;
  recommendation: string;
}

export interface DiseaseCandidate {
  rank: number;
  disease_name: string;
  orpha_code: string;
  omim_id?: string;
  score: number;
  phenotype_match_score: number;
  genotype_match_score: number;
  prevalence: string;
  inheritance_pattern: string;
  matched_symptoms: string[];
  unmatched_symptoms: string[];
  supporting_genes: string[];
  reasoning: string;
}

export interface DeepRareResult {
  candidates: DiseaseCandidate[];
  total_variants_analyzed: number;
  phenotype_terms_matched: number;
  model_version: string;
  confidence_note: string;
}

export interface ACMGResult {
  variants: VariantResult[];
  pathogenic_count: number;
  likely_pathogenic_count: number;
  vus_count: number;
  benign_count: number;
  actionable_variants: string[];
  classifier_version: string;
}

export interface StructuralImpact {
  impact_type: string;
  severity: "High" | "Medium" | "Low";
  affected_domain: string;
  description: string;
}

export interface ProteinStructure {
  gene: string;
  uniprot_id: string;
  pdb_id?: string;
  structure_url: string;
  plddt_score: number;
  variant_position: number;
  wild_type_residue: string;
  mutant_residue: string;
}

export interface AlphaFoldResult {
  gene: string;
  variant: string;
  wild_type_structure: ProteinStructure;
  mutant_structure: ProteinStructure;
  rmsd: number;
  structural_impacts: StructuralImpact[];
  pathogenicity_upgrade: boolean;
  upgraded_from?: string;
  upgraded_to?: string;
  functional_summary: string;
  pdb_wild_type: string;
  pdb_mutant: string;
}

export interface PipelineResult {
  session_id: string;
  patient_name: string;
  deeprare: DeepRareResult;
  acmg: ACMGResult;
  alphafold: AlphaFoldResult[];
  summary: string;
  time_to_diagnosis_estimate: string;
  report_url?: string;
}
