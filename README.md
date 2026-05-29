# 🧬 RareDx — AI-Powered Rare Disease Diagnostic Pipeline

> **From symptom to molecular cause in minutes — not years.**

RareDx combines three state-of-the-art AI tools into a single transparent diagnostic pipeline that compresses the average 5–7 year rare disease diagnostic odyssey into a streamlined, evidence-backed workflow.

---

## 🔬 The Three-Tool Pipeline

| Step | Tool | What it does |
|------|------|-------------|
| **1** | **DeepRare** | Ranks likely rare diseases by combining phenotype (symptoms) + genotype (variants) with transparent scoring |
| **2** | **ACMG Classifier** | Classifies each genetic variant as Pathogenic / Likely Pathogenic / VUS / Benign using ACMG/AMP 2015 criteria |
| **3** | **AlphaFold3** | Visualizes wild-type vs. mutant 3D protein structure to explain *why* a variant is damaging at the molecular level |

---

## 🖥️ Tech Stack

### Frontend
- **React 18** + **TypeScript** + **Vite**
- **Tailwind CSS** + **shadcn/ui** design system
- **Framer Motion** — animated pipeline stepper
- **3Dmol.js** — interactive 3D protein viewer
- **Zustand** — global state (pipeline progress, results)
- **React Hook Form** + **Zod** — form validation
- **SSE** (Server-Sent Events) — live pipeline streaming

### Backend
- **FastAPI** (Python 3.12)
- **Pydantic v2** — typed request/response models
- **SSE streaming** — real-time pipeline progress
- **ReportLab** — PDF report generation
- Custom VCF 4.1/4.2 parser

### Infrastructure
- **Docker** + **Docker Compose**
- **Nginx** reverse proxy (SSE-aware configuration)

---

## 🚀 Quick Start

### Option A — Docker (recommended)

```bash
git clone <repo>
cd Genoma
cp .env.example .env
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/docs

### Option B — Local Development

**Backend:**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## 📁 Project Structure

```
Genoma/
├── backend/
│   ├── app/
│   │   ├── main.py                   # FastAPI app + middleware
│   │   ├── api/routes/
│   │   │   ├── pipeline.py           # SSE pipeline endpoint
│   │   │   ├── report.py             # PDF generation endpoint
│   │   │   └── demo.py               # Pre-loaded demo cases
│   │   ├── services/
│   │   │   ├── deeprare_service.py   # Disease ranking (mock → Phase 2: API)
│   │   │   ├── acmg_service.py       # ACMG classification (mock → Phase 2: ClinVar)
│   │   │   ├── alphafold_service.py  # Structure prediction (mock → Phase 2: EBI API)
│   │   │   └── report_service.py     # PDF report with ReportLab
│   │   ├── models/
│   │   │   ├── patient.py            # Patient input schema
│   │   │   └── pipeline.py           # Pipeline result types
│   │   ├── core/
│   │   │   ├── config.py             # Settings (pydantic-settings)
│   │   │   └── mock_data.py          # 3 realistic demo cases
│   │   └── utils/
│   │       └── vcf_parser.py         # VCF 4.1/4.2 parser
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── HomePage.tsx          # Landing with demo case cards
│   │   │   ├── DiagnosticsPage.tsx   # Patient form + live stepper
│   │   │   └── ResultsPage.tsx       # Tabbed results + export
│   │   ├── components/
│   │   │   ├── patient-form/
│   │   │   │   ├── PatientForm.tsx   # 4-step wizard
│   │   │   │   ├── SymptomsInput.tsx # Tag-style symptom entry
│   │   │   │   ├── VcfUploader.tsx   # Drag-and-drop VCF
│   │   │   │   └── ParentSection.tsx # Family history accordions
│   │   │   ├── pipeline/
│   │   │   │   └── PipelineStepper.tsx # Live animated stages
│   │   │   ├── results/
│   │   │   │   ├── DeepRarePanel.tsx # Disease ranking cards
│   │   │   │   ├── ACMGPanel.tsx     # Variant classification
│   │   │   │   └── AlphaFoldPanel.tsx # 3D protein viewer
│   │   │   └── layout/
│   │   │       ├── Layout.tsx
│   │   │       └── Navbar.tsx
│   │   ├── store/
│   │   │   ├── themeStore.ts         # Dark/light mode (persisted)
│   │   │   └── pipelineStore.ts      # Pipeline events + results
│   │   ├── types/
│   │   │   ├── pipeline.ts           # Full result type definitions
│   │   │   └── patient.ts            # Patient form types
│   │   └── lib/utils.ts              # cn(), badge helpers
│   └── Dockerfile
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🎭 Demo Cases

Three pre-loaded realistic cases are available from the home page:

| Case | Gene | Variant | Mechanism |
|------|------|---------|-----------|
| **Marfan Syndrome** | FBN1 | c.3463C>T | cbEGF domain disulfide disruption |
| **Hereditary Breast Cancer** | BRCA1 | c.5266dupC | BRCT domain truncation + NMD |
| **Wilson's Disease** | ATP7B | Compound het. | ATP-binding site collapse |

---

## 🔌 Phase 2 — Wiring Real APIs

Each service has a clearly marked integration point:

### DeepRare
```python
# backend/app/services/deeprare_service.py
# Replace _build_mock_result() with:
async def _call_deeprare_api(symptoms, variants):
    async with httpx.AsyncClient() as c:
        return await c.post(
            "https://api.deeprare.com/v1/rank",
            headers={"Authorization": f"Bearer {settings.DEEPRARE_API_KEY}"},
            json={"hpo_terms": symptoms, "variants": variants}
        )
```

### ACMG
```python
# backend/app/services/acmg_service.py
# Replace _infer_classification() with ClinVar E-utilities:
# https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
# + local ACMG rule engine (InterVar / CharGer)
```

### AlphaFold3
```python
# backend/app/services/alphafold_service.py
# Wild-type:
pdb_wt = await fetch(f"https://alphafold.ebi.ac.uk/files/AF-{uniprot}-F1-model_v4.pdb")
# Mutant: submit to AlphaFold3 server (ColabFold API or local inference)
```

---

## 📋 Patient Input Fields

The intake form collects:

- **Demographics**: Name, DOB, sex, race/ethnicity (NIH standard)
- **Symptoms**: Tag-style HPO term entry (e.g. Arachnodactyly, Ectopia lentis)
- **Diseases**: Suspected diagnoses for priors
- **Clinical**: Age of onset, clinical notes
- **Family**: Inheritance pattern, consanguinity, sibling count
- **Father / Mother**: Affected status, age, age of onset, known conditions, phenotype description, deceased/cause
- **VCF**: Drag-and-drop upload (VCF 4.1/4.2, up to 50 MB)

---

## 📄 API Reference

Full interactive docs at `http://localhost:8000/api/docs`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/pipeline/run` | Run full pipeline (SSE stream) |
| `POST` | `/api/report/generate` | Generate PDF report |
| `GET` | `/api/demo/cases` | List demo cases |
| `GET` | `/api/demo/cases/{id}` | Get demo patient data |
| `GET` | `/api/health` | Health check |

---

## ⚠️ Disclaimer

RareDx is a **research and demonstration tool**. All results in Phase 1 are AI-generated mock outputs and do **not** constitute clinical diagnoses. All findings must be reviewed and validated by a qualified medical geneticist before any clinical use.

---

## 📜 License

MIT
