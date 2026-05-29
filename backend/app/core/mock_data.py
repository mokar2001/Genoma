"""
Realistic mock data for three pre-loaded demo cases.
Replace service calls with real API integrations in Phase 2.
"""

DEMO_CASES = {
    "marfan": {
        "label": "Marfan Syndrome — FBN1 Pathogenic Variant",
        "patient": {
            "first_name": "James",
            "last_name": "Hartwell",
            "date_of_birth": "1998-03-14",
            "sex": "Male",
            "ethnicity": "White",
            "symptoms": [
                "Arachnodactyly",
                "Pectus excavatum",
                "Ectopia lentis",
                "Aortic root dilation",
                "Scoliosis",
                "Tall stature",
                "Hypermobility",
            ],
            "suspected_diseases": ["Marfan syndrome", "Loeys-Dietz syndrome"],
            "clinical_notes": "Patient presents with classic marfanoid habitus. Echo shows aortic root Z-score +3.2.",
            "age_of_onset": 14,
            "familial_type": "Autosomal Dominant",
            "consanguinity": False,
            "father": {
                "is_affected": True,
                "age": 52,
                "age_of_onset": 18,
                "known_conditions": "Aortic aneurysm, lens dislocation",
                "phenotype_description": "Tall, slender build, underwent aortic root replacement at age 44.",
                "is_deceased": False,
            },
            "mother": {
                "is_affected": False,
                "age": 49,
                "known_conditions": "None",
                "phenotype_description": "Healthy, no connective tissue abnormalities.",
                "is_deceased": False,
            },
        },
    },
    "brca1": {
        "label": "Hereditary Breast Cancer — BRCA1 c.5266dupC",
        "patient": {
            "first_name": "Sarah",
            "last_name": "Mitchell",
            "date_of_birth": "1985-07-22",
            "sex": "Female",
            "ethnicity": "Multiracial",
            "symptoms": [
                "Breast lump (right)",
                "Family history of early-onset breast cancer",
                "Elevated CA 15-3",
                "Axillary lymphadenopathy",
            ],
            "suspected_diseases": ["Hereditary breast-ovarian cancer syndrome"],
            "clinical_notes": "3 first-degree relatives with breast or ovarian cancer. Mother diagnosed at 38.",
            "age_of_onset": 37,
            "familial_type": "Autosomal Dominant",
            "consanguinity": False,
            "father": {
                "is_affected": False,
                "age": 68,
                "known_conditions": "Type 2 diabetes",
                "phenotype_description": "No cancer history.",
                "is_deceased": False,
            },
            "mother": {
                "is_affected": True,
                "age": None,
                "age_of_onset": 38,
                "known_conditions": "Breast cancer, ovarian cancer",
                "phenotype_description": "Diagnosed with bilateral breast cancer at 38. Ovarian cancer at 44.",
                "is_deceased": True,
                "cause_of_death": "Metastatic ovarian carcinoma",
            },
        },
    },
    "wilson": {
        "label": "Wilson's Disease — ATP7B Compound Heterozygous",
        "patient": {
            "first_name": "Amir",
            "last_name": "Farahani",
            "date_of_birth": "2005-11-03",
            "sex": "Male",
            "ethnicity": "Middle Eastern or North African",
            "symptoms": [
                "Kayser-Fleischer rings",
                "Elevated serum copper",
                "Hepatomegaly",
                "Tremor",
                "Dysarthria",
                "Low ceruloplasmin",
                "Behavioral changes",
            ],
            "suspected_diseases": ["Wilson's disease", "Autoimmune hepatitis"],
            "clinical_notes": "Slit-lamp confirms KF rings. 24h urine copper 320 µg (normal <40). Liver biopsy pending.",
            "age_of_onset": 16,
            "familial_type": "Autosomal Recessive",
            "consanguinity": True,
            "father": {
                "is_affected": False,
                "age": 48,
                "known_conditions": "Carrier status suspected",
                "phenotype_description": "Mildly elevated liver enzymes on routine labs. Asymptomatic.",
                "is_deceased": False,
            },
            "mother": {
                "is_affected": False,
                "age": 45,
                "known_conditions": "Carrier status suspected",
                "phenotype_description": "No symptoms. Carrier confirmed by ATP7B sequencing.",
                "is_deceased": False,
            },
        },
    },
}


# ─── Mock VCF variants per case ──────────────────────────────────────────────

MOCK_VARIANTS = {
    "marfan": [
        {
            "gene": "FBN1",
            "cdna_change": "c.3463C>T",
            "protein_change": "p.Arg1155Cys",
            "chromosome": "15",
            "position": 48_749_382,
            "ref": "C",
            "alt": "T",
            "zygosity": "Heterozygous",
            "gnomad_af": 0.000004,
        }
    ],
    "brca1": [
        {
            "gene": "BRCA1",
            "cdna_change": "c.5266dupC",
            "protein_change": "p.Gln1756ProfsTer25",
            "chromosome": "17",
            "position": 43_057_051,
            "ref": "C",
            "alt": "CC",
            "zygosity": "Heterozygous",
            "gnomad_af": 0.000012,
        }
    ],
    "wilson": [
        {
            "gene": "ATP7B",
            "cdna_change": "c.3207C>A",
            "protein_change": "p.His1069Gln",
            "chromosome": "13",
            "position": 52_526_723,
            "ref": "C",
            "alt": "A",
            "zygosity": "Heterozygous",
            "gnomad_af": 0.000031,
        },
        {
            "gene": "ATP7B",
            "cdna_change": "c.2755C>T",
            "protein_change": "p.Arg919Trp",
            "chromosome": "13",
            "position": 52_533_106,
            "ref": "C",
            "alt": "T",
            "zygosity": "Heterozygous",
            "gnomad_af": 0.000008,
        },
    ],
}


# ─── Minimal PDB-like coordinates for viewer (real data from EBI in Phase 2) ─

MOCK_PDB_URLS = {
    "FBN1_WT": "https://alphafold.ebi.ac.uk/files/AF-P35555-F1-model_v4.pdb",
    "BRCA1_WT": "https://alphafold.ebi.ac.uk/files/AF-P38398-F1-model_v4.pdb",
    "ATP7B_WT": "https://alphafold.ebi.ac.uk/files/AF-P35670-F1-model_v4.pdb",
}
