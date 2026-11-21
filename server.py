# /// script
# requires-python = ">=3.11"
# dependencies = ["mcp>=1.0,<2", "httpx", "cryptography==44.0.3"]
# ///
"""Minimal MCP server exposing the DeepSeek Web Search API over stdio.

Single file, one tool (`web_search`), no configuration beyond the
DEEPSEEK_API_KEY environment variable. Tool parameter names stay compatible
with mcp-server-askecho-search-infinity so existing prompts keep working.

Not affiliated with DeepSeek. Search requests are billed to your own DeepSeek
account (about 5 CNY per 1,000 successful requests at the time of writing).
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import httpx
from mcp.server.fastmcp import FastMCP

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
SEARCH_URL = "https://api.deepseek.com/v1/tools/search"
REQUEST_TIMEOUT_SECONDS = 30

mcp = FastMCP("deepseek-web-search")

_TIMERANGE_DAYS = {
    "OneDay": 1,
    "OneWeek": 7,
    "OneMonth": 30,
    "OneYear": 365,
}


def _build_query(query: str, sites: str, block_hosts: str, time_range: str) -> str:
    """Compose the final query, translating filter params to DeepSeek operators."""
    parts = [query.strip()]
    if sites:
        site_list = [s.strip() for s in sites.split("|") if s.strip()][:20]
        if site_list:
            parts.append("(" + " OR ".join(f"site:{s}" for s in site_list) + ")")
    if block_hosts:
        for host in [h.strip() for h in block_hosts.split("|") if h.strip()][:5]:
            parts.append(f"-site:{host}")
    if time_range in _TIMERANGE_DAYS:
        after = (
            datetime.now(timezone.utc) - timedelta(days=_TIMERANGE_DAYS[time_range])
        ).strftime("%Y-%m-%d")
        parts.append(f"after:{after}")
    return " ".join(p for p in parts if p)


@mcp.tool()
def web_search(
    Query: str,
    Count: int = 10,
    SearchType: str = "web",
    NeedContent: bool = False,
    NeedUrl: bool = True,
    Sites: str = "",
    BlockHosts: str = "",
    Industry: str = "",
    QueryRewrite: bool = True,
    ContentFormats: str = "text",
    TimeRange: str = "",
    AuthLevel: int = 0,
) -> dict:
    """Search the web via the DeepSeek Search API.

    Args:
        Query: Search keywords, 1~128 characters. Supports operators:
            site:/-site: (host filter), "exact phrase", -exclude,
            lang:zh,en, after:/before: (YYYY-MM-DD), combinable.
        Count: Number of results, 1~50, default 10.
        SearchType: Only "web" is supported; DeepSeek has no image search.
        NeedContent: Whether to return page content in each result.
        NeedUrl: Kept for compatibility; DeepSeek always returns URLs.
        Sites: Pipe-separated allowlist, e.g. "github.com|docs.a.com"
            (max 20), translated to site: operators.
        BlockHosts: Pipe-separated blocklist, e.g. "spam.com" (max 5),
            translated to -site: operators.
        Industry: Not supported by DeepSeek; accepted and ignored.
        QueryRewrite: Kept for compatibility; DeepSeek reranks server-side.
        ContentFormats: Kept for compatibility; content is returned as-is.
        TimeRange: OneDay/OneWeek/OneMonth/OneYear, translated to after:.
        AuthLevel: 0 = no filter; 1 = keep only results with authority >= 3.
    """
    if not API_KEY:
        return {"error": {"message": "DEEPSEEK_API_KEY is not configured"}}
    query = (Query or "").strip()
    if not query:
        return {"error": {"message": "Query must not be empty"}}
    if SearchType and SearchType.strip().lower() != "web":
        return {"error": {"message": "DeepSeek search only supports SearchType 'web'"}}
    count = max(1, min(50, int(Count) if Count else 10))

    final_query = _build_query(query, Sites, BlockHosts, TimeRange)
    payload = {"query": final_query, "count": count, "need_content": bool(NeedContent)}

    try:
        resp = httpx.post(
            SEARCH_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        return {"error": {"message": f"DeepSeek search request failed: {exc}"}}

    if resp.status_code != 200:
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text[:500]
        return {"error": {"status": resp.status_code, "message": detail}}

    data = resp.json()
    results = data.get("results", [])
    if AuthLevel and int(AuthLevel) >= 1:
        results = [r for r in results if (r.get("authority") or 0) >= 3]
    return {
        "provider": "deepseek",
        "query": final_query,
        "count": len(results),
        "results": results,
    }


if __name__ == "__main__":
    if not API_KEY:
        print("DEEPSEEK_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)
    mcp.run()
