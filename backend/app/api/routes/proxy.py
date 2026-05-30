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
]


@router.get("/pdb")
async def proxy_pdb(url: str = Query(...)):
    # Restrict to known safe hosts only
    from urllib.parse import urlparse
    host = urlparse(url).netloc
    if not any(host.endswith(h) for h in ALLOWED_HOSTS):
        raise HTTPException(status_code=400, detail="Host not allowed")

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"Accept": "text/plain"})
            if resp.status_code != 200:
                raise HTTPException(status_code=resp.status_code, detail="Upstream error")
            return Response(
                content=resp.content,
                media_type="text/plain",
                headers={"Access-Control-Allow-Origin": "*"},
            )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
