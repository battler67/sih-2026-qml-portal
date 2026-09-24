from __future__ import annotations

import os
import time
from typing import Any

import httpx

from .cache import TtlCache
from .exceptions import NcbiUnavailableError
from .rate_limiter import RateLimiter


class NcbiClient:
    eutils_base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    datasets_base = "https://api.ncbi.nlm.nih.gov/datasets/v2"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        tool_name: str | None = None,
        email: str | None = None,
        timeout_seconds: float | None = None,
        max_retries: int | None = None,
        cache_ttl_seconds: int | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("NCBI_API_KEY", "")
        self.tool_name = tool_name or os.getenv("NCBI_TOOL_NAME", "quantum_dna_search")
        self.email = email or os.getenv("NCBI_DEVELOPER_EMAIL", "")
        self.timeout_seconds = float(timeout_seconds or os.getenv("NCBI_REQUEST_TIMEOUT_SECONDS", "30"))
        self.max_retries = int(max_retries or os.getenv("NCBI_MAX_RETRIES", "3"))
        ttl = int(cache_ttl_seconds or os.getenv("NCBI_CACHE_TTL_SECONDS", "86400"))
        self.cache = TtlCache(ttl)
        rate = 10.0 if self.api_key else 3.0
        self.rate_limiter = RateLimiter(rate)
        self.http = http_client or httpx.Client(timeout=self.timeout_seconds)

    def _params(self, params: dict[str, Any] | None) -> dict[str, Any]:
        merged = dict(params or {})
        if self.tool_name:
            merged.setdefault("tool", self.tool_name)
        if self.email:
            merged.setdefault("email", self.email)
        if self.api_key:
            merged.setdefault("api_key", self.api_key)
        return merged

    def get_text(self, url: str, params: dict[str, Any] | None = None, *, cache_key: str | None = None) -> str:
        cached = self.cache.get(cache_key or f"text:{url}:{params}") if cache_key is not None else None
        if cached is not None:
            return str(cached)
        response = self._request("GET", url, params=self._params(params))
        text = response.text
        if cache_key is not None:
            self.cache.set(cache_key, text)
        return text

    def post_text(self, url: str, data: dict[str, Any] | None = None, *, cache_key: str | None = None) -> str:
        cached = self.cache.get(cache_key or f"post-text:{url}:{data}") if cache_key is not None else None
        if cached is not None:
            return str(cached)
        response = self._request("POST", url, data=self._params(data))
        text = response.text
        if cache_key is not None:
            self.cache.set(cache_key, text)
        return text

    def get_json(self, url: str, params: dict[str, Any] | None = None, *, cache_key: str | None = None) -> dict[str, Any]:
        cached = self.cache.get(cache_key or f"json:{url}:{params}") if cache_key is not None else None
        if cached is not None:
            return dict(cached)
        response = self._request("GET", url, params=self._params(params))
        data = response.json()
        if not isinstance(data, dict):
            raise NcbiUnavailableError("NCBI returned an unexpected response shape")
        if cache_key is not None:
            self.cache.set(cache_key, data)
        return data

    def get_bytes(self, url: str, params: dict[str, Any] | None = None, *, cache_key: str | None = None) -> bytes:
        cached = self.cache.get(cache_key or f"bytes:{url}:{params}") if cache_key is not None else None
        if cached is not None:
            return bytes(cached)
        response = self._request("GET", url, params=self._params(params))
        data = response.content
        if cache_key is not None:
            self.cache.set(cache_key, data)
        return data

    def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self.rate_limiter.wait()
            try:
                response = self.http.request(method, url, timeout=self.timeout_seconds, **kwargs)
                if response.status_code not in {429, 500, 502, 503, 504}:
                    response.raise_for_status()
                    return response
                last_error = NcbiUnavailableError(f"NCBI temporary error: HTTP {response.status_code}")
            except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_error = exc
            if attempt < self.max_retries:
                time.sleep(min(2.0**attempt, 8.0))
        raise NcbiUnavailableError("NCBI is unavailable after retries") from last_error

    def eutils_url(self, endpoint: str) -> str:
        return f"{self.eutils_base}/{endpoint}.fcgi"

    def datasets_url(self, path: str) -> str:
        return f"{self.datasets_base}/{path.lstrip('/')}"
