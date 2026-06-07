import base64
from docling_serve.datamodel.responses import ConvertDocumentResponse

from app.config.settings import DoclingConfig
from app.config.docling_options import ConvertDocumentsRequestOptions
from app.config.logging import logger
from app.clients.core import HTTPClient  # your shared core client
from app.config.docling_options import convert_options

class DoclingClient:
    CONVERSION_PATH = "/v1/convert/source"
    ASYNC_CONVERSION_PATH = "v1/convert/source/async"
    ASYNC_CHUNKING_PATH = "/v1/chunk/hybrid/source/async"
    TASK_STATUS_POLL_PATH = "/v1/status/poll"
    TASK_RESULT_PATH = "/v1/result"
    TASK_STATUS_WS_PATH = "/v1/status/ws"
    HEALTH = "/health"
    
    def __init__(
        self,
        config: DoclingConfig,
        convert_options: ConvertDocumentsRequestOptions = convert_options,
    ):
        self.http = HTTPClient(str(config.base_url), timeout=60*60)
        self.config = config
        self.convert_options = convert_options

    async def close(self):
        await self.http.close()

    async def is_healthy(self) -> bool:
        try:
            response = await self.http.request("GET", self.HEALTH)
            return response.status_code == 200
        except Exception as e:
            logger.exception("llama cpp currently not healthy", extra={"extra": {"exception": str(e)}})
            return False

    async def sync_convert_pdf(self, content: bytes, pdf_name: str) -> ConvertDocumentResponse:
        payload = {
            "sources": [
                {
                    "base64_string": base64.b64encode(content).decode(),
                    "filename": pdf_name,
                    "kind": "file",
                }
            ],
            "options": self.convert_options.model_dump(),
        }

        response = await self.http.request(
            "POST",
            self.CONVERSION_PATH,   # <-- now PATH, not full URL
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        docling_response = ConvertDocumentResponse(**response.json())
        return docling_response