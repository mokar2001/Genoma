"""
Knowledge Searcher Agent Server
Queries PubMed, Orphanet, and other free knowledge sources for disease evidence.
All APIs are free and require no key.
"""
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

PUBMED_ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
ORPHANET_API = "https://api.orphacode.org/EN/ClinicalEntity"


async def search_knowledge(query: str, hpo_ids: list[str] = None) -> dict:
    """
    Search multiple knowledge sources for evidence about a disease or symptom set.
    Returns aggregated evidence for use in LLM context.
    """
    results: dict = {}

    async with httpx.AsyncClient(timeout=10.0) as client:
        pubmed = await _search_pubmed(client, query)
        if pubmed:
            results["pubmed"] = pubmed

        orphanet = await _search_orphanet(client, query)
        if orphanet:
            results["orphanet"] = orphanet

    return results


async def _search_pubmed(client: httpx.AsyncClient, query: str) -> list[dict]:
    """Search PubMed for relevant literature."""
    try:
        search_resp = await client.get(
            PUBMED_ESEARCH,
            params={
                "db": "pubmed",
                "term": f"{query} rare disease diagnosis",
                "retmax": 3,
                "retmode": "json",
                "sort": "relevance",
            },
        )
        if search_resp.status_code != 200:
            return []

        ids = search_resp.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        summary_resp = await client.get(
            PUBMED_ESUMMARY,
            params={"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
        )
        if summary_resp.status_code != 200:
            return []

        result_data = summary_resp.json().get("result", {})
        articles = []
        for pmid in ids:
            doc = result_data.get(pmid, {})
            if doc:
                articles.append({
                    "pmid": pmid,
                    "title": doc.get("title", ""),
                    "authors": [a.get("name", "") for a in doc.get("authors", [])[:3]],
                    "pubdate": doc.get("pubdate", ""),
                    "source": doc.get("source", ""),
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                })
        return articles
    except Exception as e:
        logger.debug(f"PubMed search error: {e}")
        return []


async def _search_orphanet(client: httpx.AsyncClient, disease_name: str) -> Optional[dict]:
    """Search Orphanet for disease information."""
    try:
        resp = await client.get(
            f"{ORPHANET_API}/Name/{disease_name}/",
            headers={"accept": "application/json"},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                entry = data[0] if isinstance(data, list) else data
                return {
                    "orpha_code": entry.get("OrphaCode"),
                    "name": entry.get("Name", {}).get("label", disease_name),
                    "url": f"https://www.orpha.net/consor/cgi-bin/OC_Exp.php?Expert={entry.get('OrphaCode')}",
                    "source": "Orphanet",
                }
    except Exception as e:
        logger.debug(f"Orphanet search error: {e}")
    return None
