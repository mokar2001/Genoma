FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download BioLORD model so it's baked into the image
# Falls back to MiniLM if BioLORD fails (network issues)
RUN python -c "\
from sentence_transformers import SentenceTransformer; \
try: \
    SentenceTransformer('FremyCompany/BioLORD-2023-C'); \
    print('BioLORD loaded') \
except Exception as e: \
    print(f'BioLORD failed ({e}), downloading fallback'); \
    SentenceTransformer('all-MiniLM-L6-v2'); \
    print('MiniLM loaded') \
"

COPY . .

# Cache directory for HPO terms + embeddings (mount as volume for persistence)
RUN mkdir -p /app/cache

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
