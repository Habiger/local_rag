import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    retry_if_exception_type,
)
from urllib.parse import urljoin

from app.config.logging import logger


class HTTPServerError(Exception):
    pass

class HTTPClientError(Exception):
    pass

class HTTPClientTooManyRequestsError(Exception):
    pass

class HTTPTransportError(Exception):
    pass

RETRY_POLICY = retry(
            stop=stop_after_attempt(3),
            wait=wait_random_exponential(multiplier=1, min=2, max=20),
            reraise=True,
            retry=(
                retry_if_exception_type(HTTPServerError)
                | retry_if_exception_type(HTTPClientTooManyRequestsError)
                | retry_if_exception_type(HTTPTransportError)
            ),
        )

class HTTPClient:
    def __init__(self, base_url: str, timeout=60*60):
        self.base_url = base_url.rstrip("/") + "/"
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self.client.aclose()

    def _create_url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))
    
    @staticmethod
    def _map_status_error(status_code: int) -> Exception:
        if status_code == 429:
            return HTTPClientTooManyRequestsError("429 Too Many Requests")

        if 400 <= status_code < 500:
            return HTTPClientError(f"Client error: {status_code}")

        if 500 <= status_code < 600:
            return HTTPServerError(f"Server error: {status_code}")

        return Exception(f"Unexpected HTTP status: {status_code}")

    @RETRY_POLICY
    async def request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        headers: dict | None = None,
    ):
        url = self._create_url(path)
        try:
            response = await self.client.request(
                method,
                url,
                json=json,
                headers=headers,
            )
        except httpx.RequestError as e:
            logger.error(
                "HTTP transport error",
                extra={
                    "extra": {
                        "url": url, 
                        "error": str(e),
                        "error_type": type(e).__name__
                    }
                },
            )
            raise HTTPTransportError(str(e)) from e

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            exc = self._map_status_error(e.response.status_code)

            logger.error(
                "HTTP error",
                extra={
                    "extra":{
                        "status_code": e.response.status_code,
                        "url": url,
                        "response_snippet": e.response.text[:1000],
                        "error_type": type(exc).__name__,
                    }
                },
            )

            raise exc from e

        return response