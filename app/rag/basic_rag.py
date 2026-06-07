import asyncio
import asyncpg
import sys

from enum import Enum
from dataclasses import dataclass
from openai import AsyncOpenAI

# use openai library for llms? vs llamaindex
# use custom retriever logic vs llamaindex?

from pydantic_ai import Agent, Embedder, RunContext
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel

from app.config.settings import llamacpp_config, LlamaCppConfig
from app.clients.embedding_client import AsyncEmbeddingClient, EmbeddingModel
from app.clients.db_manager_async import AsyncDatabaseClient

class Models(str, Enum):
    qwen3_3_6_35B_A3B= "Qwen3.6-35B-A3B"

class Qwen3Embedder(Embedder):
    def __init__(self):
        pass

llamacpp_client = AsyncOpenAI(
    base_url = llamacpp_config.openai_compatible_v1_endpoint,
    api_key="dummy-key" # for my local llama.cpp server no api-key has been set
)

provider = OpenAIProvider(
    openai_client=llamacpp_client,
)
llm = OpenAIChatModel(
    model_name=Models.qwen3_3_6_35B_A3B.value,
    provider=provider,
)


#embedder = Embedder()

query = "Tell me the difference between 4 and two."

@dataclass
class Deps:
    embedding_client: AsyncEmbeddingClient
    db: AsyncDatabaseClient
    
agent = Agent(
    model = llm,
    deps_type = Deps
)

@agent.tool
async def retrieve(context: RunContext[Deps], search_query: str) -> str:
    db = context.deps.db
    embedding = context.deps.embedding_client
    
    embedded_query = await embedding.embed(search_query, EmbeddingModel.QWEN3_EMBEDDING_06B_Q8)
    search_result = await db.similarity_search(embedded_query, EmbeddingModel.QWEN3_EMBEDDING_06B_Q8, limit=10)
    print("\n\nretrievaltool\n\n")
    print(search_result)
    return str(search_result)
        
async def run_agent(question: str):
    embedding_client = AsyncEmbeddingClient(llamacpp_config)
    db = AsyncDatabaseClient()
    deps = Deps(embedding_client, db)
    answer = await agent.run(question, deps=deps)
    print("----"*5)
    print(answer)
    print("----"*5)
    print(answer.all_messages())
    print("----"*5)
    print(answer.output)
    

if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    question = "search for things related to model based clustering"
    asyncio.run(run_agent(question))



