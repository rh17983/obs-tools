import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional
import time

import aiohttp
import yaml

from aiohttp import (
    ClientConnectorError,
    ClientResponseError,
    ClientSSLError,
    InvalidURL,
    TooManyRedirects,
)

# ---- Config ----

# Maximum number of concurrent requests
CONCURRENCY = 80

# Request timeout in seconds
TIMEOUT_SECONDS = 5

# ----------------------------
# Utility functions
# ----------------------------

def _normalize_url(url: str) -> str:
    """Ensure URL has a scheme (https://). If empty, return as is."""
    if not url:
        return url

    return url if "://" in url else f"https://{url}"


async def _fetch_head_or_get(session: aiohttp.ClientSession, url: str) -> Tuple[Optional[int], str, str]:
    """Try to fetch URL with HEAD method first; if it fails, use GET with Range header. Return (status_code, reason, final_url)."""

    # Request with HEAD method first. Requesting headers only.
    try:
        async with session.head(url, allow_redirects=True) as resp:
            return resp.status, resp.reason or "", str(resp.url)
    except ClientResponseError as e:
        if e.status not in (400, 401, 403, 404, 405, 500, 501, 502, 503, 504):
            return e.status, e.message or "HTTP error", url
    except Exception:
        pass

    # Fallback to GET request with Range header to minimize data transfer. Requesting first byte only.
    try:
        headers = {"Range": "bytes=0-0"}
        async with session.get(url, allow_redirects=True, headers=headers) as resp:
            return resp.status, resp.reason or "", str(resp.url)
    except ClientResponseError as e:
        return e.status, e.message or "HTTP error", url


def _exc_reason(exc: Exception) -> str:
    """Convert exception to a human-readable reason string."""

    if isinstance(exc, asyncio.TimeoutError):
        return "timeout"
    if isinstance(exc, ClientConnectorError):
        return f"connection error: {exc.os_error.strerror if getattr(exc, 'os_error', None) else str(exc)}"
    if isinstance(exc, ClientSSLError):
        return "ssl error"
    if isinstance(exc, TooManyRedirects):
        return "too many redirects"
    if isinstance(exc, InvalidURL):
        return "invalid url"

    return exc.__class__.__name__ + (f": {exc}" if str(exc) else "")


# ----------------------------
# Core async logic
# ----------------------------

async def check_one(url: str, session: aiohttp.ClientSession, sem: asyncio.Semaphore) -> Dict[str, Any]:
    """Check a single URL and return status dict."""

    url = _normalize_url(url)
    if not url:
        return {"ok": False, "code": None, "reason": "empty url", "final_url": None}

    # limit concurrency by semaphore to avoid overwhelming the server. maximum holders of sem is controlled by constant CONCURRENCY
    async with sem:
        try:
            code, reason, final_url = await _fetch_head_or_get(session, url)
            ok = code is not None and 200 <= code < 400
            return {
                "ok": ok,
                "code": code,
                "reason": reason or ("OK" if ok else "HTTP error"),
                "final_url": final_url,
            }
        except Exception as e:
            return {"ok": False, "code": None, "reason": _exc_reason(e), "final_url": None}


async def process(data):
    """Coroutines to process the entire data structure asynchronously. Return updated data."""

    import aiohttp

    # Create a timeout for all requests.
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)

    # Create a semaphore to limit concurrency.
    sem = asyncio.Semaphore(CONCURRENCY)

    # Build index map to correlate URLs back to their locations in the data structure.
    index_map = []

    # Collect (region_idx, region_key, site_idx, site_name, url)
    for i, region_obj in enumerate(data):
        if not isinstance(region_obj, dict):
            continue
        for region, websites in region_obj.items():
            if not isinstance(websites, list):
                continue
            for j, site_entry in enumerate(websites):
                if not isinstance(site_entry, dict):
                    continue
                for site_name, meta in site_entry.items():
                    if isinstance(meta, dict) and "link" in meta:
                        index_map.append((i, region, j, site_name, meta["link"]))

    # Perform all requests concurrently. Reuse a single ClientSession for efficiency.
    async with aiohttp.ClientSession(timeout=timeout, headers={"User-Agent": "link-checker/2.1 (+curl-compatible)"}) as session:
        """Create coroutines for all URLs to check"""
        coros = [check_one(url, session, sem) for *_, url in index_map]
        # Gather results with error handling. Return list of status dicts.
        results = await asyncio.gather(*coros)

    # Write back results. Update the original data structure with status info.
    for (i, region, j, site_name, _), status in zip(index_map, results):
        meta = data[i][region][j][site_name]
        meta["status"] = status
        data[i][region][j][site_name] = meta

    return data

# ----------------------------
# I/O helpers
# ----------------------------
def load_input(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        if path.suffix.lower() in [".yaml", ".yml"]:
            return yaml.safe_load(f)
        return json.load(f)


def save_output(path: Path, data: Any):
    with path.open("w", encoding="utf-8") as f:
        if path.suffix.lower() in [".yaml", ".yml"]:
            yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        else:
            json.dump(data, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 check_links_async.py <input.yaml|json> <output.yaml|json>")
        sys.exit(1)

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    data = load_input(in_path)

    if not isinstance(data, list):
        print("Input must be a list of region objects:")
        sys.exit(2)

    start_time = time.perf_counter()

    # Run the async processing. Blocks until complete.
    updated = asyncio.run(process(data))

    elapsed = time.perf_counter() - start_time
    print(f"Total runtime: {elapsed:.2f} seconds")

    save_output(out_path, updated)
    print(f"Wrote results to: {out_path}")


if __name__ == "__main__":
    main()
