from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from enum import Enum


class Ethnicity(str, Enum):
    WHITE = "White"
    BLACK_AA = "Black or African American"
    ASIAN = "Asian"
    HISPANIC = "Hispanic or Latino"
    NATIVE_AMERICAN = "American Indian or Alaska Native"
    PACIFIC_ISLANDER = "Native Hawaiian or Other Pacific Islander"
    MIDDLE_EASTERN = "Middle Eastern or North African"
    MULTIRACIAL = "Multiracial"
    PREFER_NOT = "Prefer not to say"
    OTHER = "Other"


class Sex(str, Enum):
    MALE = "Male"
    FEMALE = "Female"
    OTHER = "Other"
    UNKNOWN = "Unknown"


class FamilialType(str, Enum):
    SPORADIC = "Sporadic (no family history)"
    AUTOSOMAL_DOMINANT = "Autosomal Dominant"
    AUTOSOMAL_RECESSIVE = "Autosomal Recessive"
    X_LINKED = "X-Linked"
    MITOCHONDRIAL = "Mitochondrial"
    UNKNOWN = "Unknown / Suspected familial"


class ParentInfo(BaseModel):
    is_affected: bool = False
    age: Optional[int] = None
    age_of_onset: Optional[int] = None
    known_conditions: Optional[str] = None
    phenotype_description: Optional[str] = None
    is_deceased: bool = False
    cause_of_death: Optional[str] = None


class PatientInput(BaseModel):
    # Core demographics
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    sex: Sex
    ethnicity: Ethnicity

    # Clinical presentation
    symptoms: List[str] = Field(..., min_length=1)
    suspected_diseases: Optional[List[str]] = None
    clinical_notes: Optional[str] = None
    age_of_onset: Optional[int] = None

    # Family history
    familial_type: FamilialType = FamilialType.UNKNOWN
    consanguinity: bool = False
    father: Optional[ParentInfo] = None
    mother: Optional[ParentInfo] = None
    affected_siblings_count: int = 0

    # The VCF filename is stored after upload
    vcf_filename: Optional[str] = None
    vcf_session_id: Optional[str] = None
