# Celery worker image — runs bioinformatics pipelines, embeddings, scoring.
# Includes Nextflow + Java + Docker CLI so it can launch nf-core containers
# on the host Docker daemon (socket is mounted at runtime).
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NXF_HOME=/data/.nextflow

# System deps: Java (Nextflow), Docker CLI, build tools, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    ca-certificates \
    gnupg \
    procps \
    default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Docker CLI (to talk to mounted host socket)
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && chmod a+r /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

# Nextflow
RUN curl -s https://get.nextflow.io | bash \
    && mv nextflow /usr/local/bin/ \
    && chmod +x /usr/local/bin/nextflow

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model
COPY download_models.py .
RUN python download_models.py

COPY . .

RUN mkdir -p /app/cache /data

# Celery worker: solo pool is safest with subprocess-heavy bioinformatics tasks.
# Concurrency kept low because pipeline jobs are RAM/CPU heavy on an 8-core box.
CMD ["celery", "-A", "app.core.celery_app.celery", "worker", \
     "--loglevel=info", "--concurrency=2", "--pool=prefork", \
     "-Q", "pipelines,indexing,scoring,default"]
