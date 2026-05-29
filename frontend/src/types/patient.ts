export const ETHNICITIES = [
  "White",
  "Black or African American",
  "Asian",
  "Hispanic or Latino",
  "American Indian or Alaska Native",
  "Native Hawaiian or Other Pacific Islander",
  "Middle Eastern or North African",
  "Multiracial",
  "Prefer not to say",
  "Other",
] as const;

export const FAMILIAL_TYPES = [
  "Sporadic (no family history)",
  "Autosomal Dominant",
  "Autosomal Recessive",
  "X-Linked",
  "Mitochondrial",
  "Unknown / Suspected familial",
] as const;

export const SEXES = ["Male", "Female", "Other", "Unknown"] as const;

export interface ParentInfo {
  is_affected: boolean;
  age?: number;
  age_of_onset?: number;
  known_conditions?: string;
  phenotype_description?: string;
  is_deceased: boolean;
  cause_of_death?: string;
}

export interface PatientFormValues {
  first_name: string;
  last_name: string;
  date_of_birth: string;
  sex: (typeof SEXES)[number];
  ethnicity: (typeof ETHNICITIES)[number];
  symptoms: string[];
  suspected_diseases: string[];
  clinical_notes?: string;
  age_of_onset?: number;
  familial_type: (typeof FAMILIAL_TYPES)[number];
  consanguinity: boolean;
  father?: ParentInfo;
  mother?: ParentInfo;
  affected_siblings_count: number;
  vcf_file?: File;
}
