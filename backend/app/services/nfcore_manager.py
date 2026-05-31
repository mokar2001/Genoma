"""
nf-core Pipeline Manager
========================
- Lists curated nf-core pipelines relevant to rare disease genomics
- Installs them on demand via `nextflow pull <pipeline>`
- Builds resource-capped run commands for the user's 32GB / 8-core server
- Runs FASTQ/BAM -> VCF (nf-core/sarek) and returns the produced VCF path

Real Nextflow execution: the worker container has nextflow + docker CLI and the
host Docker socket mounted, so `nextflow run ... -profile docker` spawns sibling
nf-core containers on the host daemon.
"""

import os
import subprocess
import logging
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# Curated registry — the pipelines we surface in the UI.
NFCORE_REGISTRY = [
    {
        "name": "nf-core/sarek",
        "title": "Sarek — Germline & Somatic Variant Calling",
        "description": "Maps FASTQ/BAM to a reference and calls SNVs/indels/SVs (GATK, DeepVariant, Strelka). Use for WGS/WES → VCF.",
        "input": "FASTQ / BAM",
        "output": "VCF",
        "recommended": True,
        "default_tools": "deepvariant",
    },
    {
        "name": "nf-core/raredisease",
        "title": "Raredisease — Rare Disease Genomics",
        "description": "End-to-end rare disease workflow: alignment, calling, annotation (VEP), ranking (genmod). Best for diagnostic WGS.",
        "input": "FASTQ",
        "output": "Annotated VCF",
        "recommended": True,
        "default_tools": "",
    },
    {
        "name": "nf-core/sentieon",
        "title": "Sentieon — Fast Germline Calling",
        "description": "Accelerated DNA-seq germline variant calling (Sentieon DNAscope/Haplotyper). Much faster than GATK for WGS/WES.",
        "input": "FASTQ / BAM",
        "output": "VCF",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/rnaseq",
        "title": "RNA-seq — Expression Quantification",
        "description": "Quantifies gene/transcript expression (STAR/Salmon). Confirms splice variants and allele-specific expression.",
        "input": "FASTQ",
        "output": "Expression matrix",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/rnafusion",
        "title": "RNA-fusion — Gene Fusion Detection",
        "description": "Detects gene fusions from RNA-seq (Arriba, STAR-Fusion, FusionCatcher). Relevant for fusion-driven rare disorders/cancers.",
        "input": "FASTQ",
        "output": "Fusion calls",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/methylseq",
        "title": "Methylseq — DNA Methylation",
        "description": "Bisulfite sequencing analysis (Bismark/bwa-meth). For imprinting disorders and epigenetic rare disease workups.",
        "input": "FASTQ",
        "output": "Methylation calls",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/nanoseq",
        "title": "Nanoseq — Long-read (Nanopore)",
        "description": "Oxford Nanopore long-read alignment and variant/SV calling. Resolves repeat expansions and structural variants.",
        "input": "FASTQ (ONT)",
        "output": "VCF / SV",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/scrnaseq",
        "title": "scRNA-seq — Single-cell Expression",
        "description": "Single-cell RNA-seq quantification (Cell Ranger / STARsolo / Alevin). For cell-type-resolved functional analysis.",
        "input": "FASTQ",
        "output": "Cell × gene matrix",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/cutandrun",
        "title": "CUT&RUN — Protein-DNA Binding",
        "description": "Maps transcription factor / histone binding sites. Functional follow-up for regulatory variants.",
        "input": "FASTQ",
        "output": "Peaks",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/atacseq",
        "title": "ATAC-seq — Chromatin Accessibility",
        "description": "Profiles open chromatin regions. Interprets non-coding regulatory variant impact.",
        "input": "FASTQ",
        "output": "Accessibility peaks",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/taxprofiler",
        "title": "Taxprofiler — Metagenomic Profiling",
        "description": "Taxonomic classification of metagenomic reads (Kraken2, MetaPhlAn). For infection vs genetic disease triage.",
        "input": "FASTQ",
        "output": "Taxon profile",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/fetchngs",
        "title": "fetchngs — Public Data Fetcher",
        "description": "Downloads raw sequencing data from SRA/ENA/GEO by accession. Useful for fetching reference cases.",
        "input": "Accession IDs",
        "output": "FASTQ",
        "recommended": False,
        "default_tools": "",
    },
    {
        "name": "nf-core/demultiplex",
        "title": "Demultiplex — BCL → FASTQ",
        "description": "Converts raw Illumina BCL run folders to per-sample FASTQ (bcl-convert / bcl2fastq).",
        "input": "BCL run folder",
        "output": "FASTQ",
        "recommended": False,
        "default_tools": "",
    },
]


def list_registry() -> list[dict]:
    """Return the curated pipeline registry."""
    return NFCORE_REGISTRY


def get_registry_entry(name: str) -> Optional[dict]:
    for p in NFCORE_REGISTRY:
        if p["name"] == name:
            return p
    return None


def _nextflow_env() -> dict:
    env = os.environ.copy()
    env["NXF_HOME"] = settings.NXF_HOME
    env["NXF_ANSI_LOG"] = "false"
    Path(settings.NXF_HOME).mkdir(parents=True, exist_ok=True)
    return env


def install_pipeline(name: str, revision: Optional[str] = None,
                     progress_cb=None) -> dict:
    """
    Install (pull) an nf-core pipeline. Blocking — run inside a Celery task.
    Returns {success, revision, output}.
    """
    cmd = ["nextflow", "pull", name]
    if revision:
        cmd += ["-r", revision]

    logger.info(f"Installing pipeline: {' '.join(cmd)}")
    if progress_cb:
        progress_cb(10, f"Pulling {name}…")

    try:
        proc = subprocess.run(
            cmd,
            env=_nextflow_env(),
            capture_output=True,
            text=True,
            timeout=1800,  # 30 min
        )
        ok = proc.returncode == 0
        if progress_cb:
            progress_cb(100 if ok else 0, "Installed" if ok else "Install failed")
        return {
            "success": ok,
            "revision": revision or "latest",
            "output": (proc.stdout + proc.stderr)[-4000:],
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "Install timed out after 30 min"}
    except FileNotFoundError:
        return {"success": False, "output": "nextflow not found in worker image"}


def list_installed() -> list[str]:
    """List pipelines already pulled into NXF_HOME."""
    base = Path(settings.NXF_HOME) / "assets"
    if not base.exists():
        return []
    installed = []
    for org in base.iterdir():
        if org.is_dir():
            for repo in org.iterdir():
                if repo.is_dir():
                    installed.append(f"{org.name}/{repo.name}")
    return installed


def _write_resource_config(work_dir: Path) -> Path:
    """
    Write a nextflow.config that caps resources to the server budget.
    Prevents nf-core from requesting more than the box has.
    """
    cfg = work_dir / "raredx.config"
    cfg.write_text(
        f"""
process {{
    resourceLimits = [
        cpus: {settings.NF_MAX_CPUS},
        memory: '{settings.NF_MAX_MEMORY}',
        time: '{settings.NF_MAX_TIME}'
    ]
}}
docker {{
    enabled = true
    runOptions = '-u $(id -u):$(id -g)'
}}
"""
    )
    return cfg


def run_sarek(
    case_id: str,
    fastq_files: list[str],
    sample_name: str = "sample",
    wes: bool = True,
    progress_cb=None,
) -> dict:
    """
    Run nf-core/sarek FASTQ -> VCF. Blocking — call from a Celery task.

    fastq_files: list of absolute paths (R1, R2) inside the shared /data volume.
    Returns {success, vcf_path, log}.
    """
    work_root = Path(settings.DATA_DIR) / "runs" / case_id
    work_root.mkdir(parents=True, exist_ok=True)
    outdir = work_root / "sarek_out"
    workdir = work_root / "work"

    # Build a samplesheet (sarek v3 CSV format)
    samplesheet = work_root / "samplesheet.csv"
    r1 = fastq_files[0] if len(fastq_files) > 0 else ""
    r2 = fastq_files[1] if len(fastq_files) > 1 else ""
    samplesheet.write_text(
        "patient,sample,lane,fastq_1,fastq_2\n"
        f"{sample_name},{sample_name},L001,{r1},{r2}\n"
    )

    cfg = _write_resource_config(work_root)

    cmd = [
        "nextflow", "run", "nf-core/sarek",
        "-profile", "docker",
        "-c", str(cfg),
        "--input", str(samplesheet),
        "--outdir", str(outdir),
        "-work-dir", str(workdir),
        "--genome", settings.GENOME_BUILD,
        "--tools", "deepvariant",
        "-resume",
    ]
    if wes:
        cmd += ["--wes"]

    logger.info(f"Running sarek: {' '.join(cmd)}")
    if progress_cb:
        progress_cb(5, "Starting nf-core/sarek (this can take hours)…")

    log_path = work_root / "nextflow.log"
    try:
        with open(log_path, "w") as logf:
            proc = subprocess.Popen(
                cmd,
                env=_nextflow_env(),
                stdout=logf,
                stderr=subprocess.STDOUT,
                cwd=str(work_root),
            )
            # Poll for progress by tailing the log
            import time
            pct = 5
            while proc.poll() is None:
                time.sleep(15)
                pct = min(pct + 2, 95)
                if progress_cb:
                    progress_cb(pct, _tail_progress(log_path))
            rc = proc.returncode

        if rc != 0:
            return {"success": False, "vcf_path": None, "log": _read_tail(log_path)}

        vcf = _find_vcf(outdir)
        if progress_cb:
            progress_cb(100, "Variant calling complete")
        return {"success": vcf is not None, "vcf_path": str(vcf) if vcf else None,
                "log": _read_tail(log_path)}

    except FileNotFoundError:
        return {"success": False, "vcf_path": None, "log": "nextflow not installed"}
    except Exception as e:
        logger.exception("sarek run failed")
        return {"success": False, "vcf_path": None, "log": str(e)}


def _find_vcf(outdir: Path) -> Optional[Path]:
    """Locate the final VCF produced by sarek."""
    if not outdir.exists():
        return None
    candidates = list(outdir.rglob("*.vcf.gz")) + list(outdir.rglob("*.vcf"))
    # Prefer annotated/filtered germline VCFs
    for c in candidates:
        if "deepvariant" in str(c).lower() or "haplotypecaller" in str(c).lower():
            return c
    return candidates[0] if candidates else None


def _tail_progress(log_path: Path) -> str:
    line = _read_tail(log_path, lines=1).strip()
    return line[:120] if line else "Running…"


def _read_tail(path: Path, lines: int = 40) -> str:
    try:
        content = path.read_text(errors="replace").splitlines()
        return "\n".join(content[-lines:])
    except Exception:
        return ""
