from app.clients.core import HTTPClient

from app.config.logging import logger
from app.config.settings import LlamaCppConfig

class EmbeddingClient:
    EMBEDDINGS_PATH = "/v1/embeddings"
    CHAT_PATH = "/v1/chat/completions"
    RERANK_PATH = "/v1/rerank"
    HEALTH = ""

    def __init__(self, config: LlamaCppConfig):
        self.http = HTTPClient(str(config.base_url), timeout=60*30) #TODO add timout to LLamaCppConfig
        self.config = config

    async def embed(self, text: str, model: str):
        response = await self.http.request(
            "POST",
            self.EMBEDDINGS_PATH,
            json={
                "input": text,
                "model": model,
                "encoding_format": "float",
            },
        )
        data = response.json()["data"]
        return data[0]["embedding"]

    async def is_healthy(self) -> bool:
        try:
            response = await self.http.request("GET", self.HEALTH)
            return response.status_code == 200
        except Exception as e:
            logger.exception("llama cpp currently not healthy", extra={"extra": {"exception": str(e)}})
            return False

    async def close(self):
        await self.http.close()