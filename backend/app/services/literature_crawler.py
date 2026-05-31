"""
Literature Crawler (DeepRare "Knowledge Searcher")
==================================================
Crawls biomedical literature LIVE by phenotype + genotype keywords.
No pre-embedded corpus — queries are built from the case's HPO terms and genes.

Sources (all free, no key):
  - Europe PMC      (full REST search, abstracts, open access)
  - PubMed E-utils  (esearch + esummary)

Results are de-duplicated, ranked by keyword overlap, and returned with
citations (title, authors, journal, year, URL) for traceable reasoning.
"""

import asyncio
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"


async def crawl_literature(
    phenotype_terms: list[str],
    genes: list[str],
    suspected_diseases: Optional[list[str]] = None,
    max_results: int = 8,
) -> list[dict]:
    """
    Crawl literature by phenotype + gene keywords.
    Returns ranked list of {title, authors, journal, year, pmid, doi, url, snippet, source}
    """
    queries = _build_queries(phenotype_terms, genes, suspected_diseases or [])
    if not queries:
        return []

    # Fetch all queries in parallel from Europe PMC
    async with httpx.AsyncClient(timeout=15.0) as client:
        tasks = [_europepmc_search(client, q, max_results) for q in queries[:4]]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge + dedup by DOI/PMID/title
    merged: dict[str, dict] = {}
    for rl in results_lists:
        if isinstance(rl, Exception):
            continue
        for art in rl:
            key = art.get("doi") or art.get("pmid") or art.get("title", "")[:60]
            if key and key not in merged:
                merged[key] = art

    articles = list(merged.values())

    # Rank by keyword overlap with phenotype + genes
    keywords = set(k.lower() for k in (phenotype_terms + genes))
    for art in articles:
        text = (art.get("title", "") + " " + art.get("snippet", "")).lower()
        art["_relevance"] = sum(1 for kw in keywords if kw in text)

    articles.sort(key=lambda a: a.get("_relevance", 0), reverse=True)

    # Strip internal field
    for a in articles:
        a.pop("_relevance", None)

    return articles[:max_results]


def _build_queries(phenotypes: list[str], genes: list[str],
                   diseases: list[str]) -> list[str]:
    """Construct targeted literature search queries."""
    queries = []

    # Gene-centric (most specific) — gene + top phenotypes
    top_pheno = phenotypes[:3]
    for gene in genes[:2]:
        if top_pheno:
            queries.append(f'{gene} AND ({" OR ".join(top_pheno)})')
        else:
            queries.append(f"{gene} rare disease")

    # Disease-centric
    for disease in diseases[:2]:
        queries.append(f'"{disease}"')

    # Phenotype combination (when no genes)
    if not genes and len(phenotypes) >= 2:
        combo = " AND ".join(f'"{p}"' for p in phenotypes[:3])
        queries.append(combo)

    # Fallback single phenotype + rare disease
    if not queries and phenotypes:
        queries.append(f'{phenotypes[0]} rare disease')

    return queries


async def _europepmc_search(client: httpx.AsyncClient, query: str,
                            limit: int) -> list[dict]:
    """Search Europe PMC for a query."""
    try:
        resp = await client.get(EUROPE_PMC, params={
            "query": query,
            "format": "json",
            "pageSize": limit,
            "resultType": "core",
            "sort": "CITED desc",
        })
        if resp.status_code != 200:
            return []
        data = resp.json()
        results = data.get("resultList", {}).get("result", [])
        articles = []
        for r in results:
            pmid = r.get("pmid", "")
            doi = r.get("doi", "")
            articles.append({
                "title": r.get("title", "").rstrip("."),
                "authors": r.get("authorString", ""),
                "journal": r.get("journalTitle", ""),
                "year": r.get("pubYear", ""),
                "pmid": pmid,
                "doi": doi,
                "url": (
                    f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid
                    else (f"https://doi.org/{doi}" if doi else "")
                ),
                "snippet": (r.get("abstractText", "") or "")[:300],
                "citations": r.get("citedByCount", 0),
                "source": "Europe PMC",
            })
        return articles
    except Exception as e:
        logger.debug(f"Europe PMC search error for '{query}': {e}")
        return []
