# RareDx — Deployment Guide (v0.3 — Clinical Genomics Platform)

## Architecture

```
frontend (nginx) ── backend (FastAPI, API only)
                         │
   ┌─────────────────────┼──────────────────────┐
   │                     │                      │
postgres            redis (broker)           qdrant
(cases/users/jobs)   + progress pub/sub     (case vectors)
                         │
                    worker (Celery)
                    - nf-core/sarek (Nextflow + docker.sock)
                    - phenotype / similarity / literature
                    - variant scoring / AlphaFold
                         │
                  /data volume (FASTQ/BAM/VCF, AlphaMissense, models)
```

## Per-case pipeline

```
Upload (FASTQ / BAM / VCF)
  → [FASTQ] nf-core/sarek → VCF        (real Nextflow, capped 28GB/7cpu)
  → parse + annotate VCF
  → phenotype extraction (patient+parents text → HPO via BioLORD)
  → similar cases (Qdrant / RareBench)
  → literature crawl (live PubMed / Europe PMC)
  → variant prioritization (AlphaMissense + gnomAD + ClinVar + Franklin)
  → novel/rare variants → AlphaFold structural analysis
  → ranked diagnoses + evidence chain
```

## First deploy (on the server)

```bash
cd ~/Genoma
git pull

# 1. Tell the worker the HOST path of the data volume (for Nextflow docker.sock mounts)
#    Volume name = <project>_raredx_data. Project dir is "Genoma" → "genoma_raredx_data".
echo "HOST_DATA_DIR=/var/lib/docker/volumes/genoma_raredx_data/_data" >> .env

# 2. Build & start everything (first build ~15-20 min — torch + nextflow + models)
docker compose up -d --build

# 3. Watch services come up
docker compose ps
docker compose logs -f backend worker
```

Services & ports:
- Frontend → http://localhost:3000
- Backend API → http://localhost:8000/api/docs
- Postgres → 5435 · Redis → 6381 · Qdrant → 6333

## One-time: build the case similarity index (RareBench)

```bash
curl -X POST http://localhost:8000/api/system/index-cases
# Watch progress:
docker compose logs -f worker
```

This downloads RareBench (HuggingFace `chenxz/RareBench`) and embeds ~1,100 cases
into Qdrant. Idempotent — safe to call again.

## Optional: enable AlphaMissense (offline pathogenicity scores)

```bash
mkdir -p /var/lib/docker/volumes/genoma_raredx_data/_data/resources
cd /var/lib/docker/volumes/genoma_raredx_data/_data/resources
# ~1GB — pathogenicity for all missense variants (hg38)
wget https://storage.googleapis.com/dm_alphamissense/AlphaMissense_hg38.tsv.gz
tabix -s 1 -b 2 -e 2 -S 1 AlphaMissense_hg38.tsv.gz   # requires htslib/tabix
```
The worker auto-detects it at `/data/resources/AlphaMissense_hg38.tsv.gz`.

## Optional: LLM reasoning

Add to `.env` (any OpenAI-compatible endpoint — Groq/Ollama/OpenAI):
```
OPENAI_API_KEY=...
OPENAI_BASE_URL=http://172.17.0.1:11434/v1   # e.g. local Ollama
LLM_MODEL=qwen2.5:1.5b
```

## Optional: Franklin (Genoox)

```
FRANKLIN_API_KEY=...
```
The client activates automatically once the key is present.

## Install nf-core pipelines

From the UI: **Pipelines** tab → Install (runs `nextflow pull` in the worker).
Or:
```bash
docker compose exec worker nextflow pull nf-core/sarek
```

## Health checks

```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/system/status   # case index, alphamissense, franklin
```
