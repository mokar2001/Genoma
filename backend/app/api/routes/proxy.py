"""
Proxy route — fetches external resources (PDB files) server-side
to avoid CORS issues in the browser.
"""

import httpx
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import Response

router = APIRouter(prefix="/proxy", tags=["proxy"])

ALLOWED_HOSTS = [
    "alphafold.ebi.ac.uk",
    "files.rcsb.org",
    "www.rcsb.org",
    "cdn.rcsb.org",
]

# Fallback PDB sources — tried in order if primary fails
PDB_FALLBACKS = {
    "P35670": "https://files.rcsb.org/download/2ARF.pdb",   # ATP7B
    "P35555": "https://files.rcsb.org/download/1LTF.pdb",   # FBN1
    "P38398": "https://files.rcsb.org/download/1JNX.pdb",   # BRCA1
}


@router.get("/pdb")
async def proxy_pdb(url: str = Query(...)):
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if not any(host.endswith(h) for h in ALLOWED_HOSTS):
        raise HTTPException(status_code=400, detail="Host not allowed")

    # Extract UniProt ID from URL for fallback lookup
    uniprot_id = ""
    import re
    m = re.search(r"AF-([A-Z0-9]+)-F1", url)
    if m:
        uniprot_id = m.group(1)

    urls_to_try = [url]
    # Add RCSB fallback if we know the UniProt ID
    if uniprot_id and uniprot_id in PDB_FALLBACKS:
        urls_to_try.append(PDB_FALLBACKS[uniprot_id])

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        for try_url in urls_to_try:
            try:
                resp = await client.get(try_url, headers={"Accept": "text/plain"})
                if resp.status_code == 200:
                    return Response(
                        content=resp.content,
                        media_type="text/plain",
                        headers={"Access-Control-Allow-Origin": "*"},
                    )
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(f"PDB fetch failed for {try_url}: {e}")
                continue

    raise HTTPException(status_code=502, detail="All PDB sources failed — structure unavailable")
