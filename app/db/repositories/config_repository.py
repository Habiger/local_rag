from psycopg.types.json import Jsonb

from app.db.base_repository import BaseRepository

from app.domains.chunking.strategies.base import BaseChunkerOptions

from app.domains.post_conversion_processing.factory import PostProcessorOptions


class ConfigRepository(BaseRepository):

    async def get_or_create_pdf_indexing_config_id(
        self,
        post_processing_config_id: int,
        chunking_config_id: int,
        embedding_model: str,
    ) -> int:
        row = await self.fetchone(
            """
            INSERT INTO pdf_indexing_config 
            (post_processing_config_id, chunking_config_id, embedding_model)
            VALUES (%s, %s, %s)
            ON CONFLICT (post_processing_config_id, chunking_config_id, embedding_model)
            DO UPDATE SET embedding_model=EXCLUDED.embedding_model
            RETURNING pdf_indexing_config_id
            """,
            (post_processing_config_id, chunking_config_id, embedding_model),
        )
        if not row:
            raise RuntimeError("Could not create pdf_indexing_config")
        return row["pdf_indexing_config_id"]

    async def get_or_create_post_processing_config_id(
        self,
        options: PostProcessorOptions,
    ) -> int:

        row = await self.fetchone(
            """
            INSERT INTO post_processing_config
            (
                parameter
            )
            VALUES (%s)
            ON CONFLICT (parameter)
            DO UPDATE SET
                parameter=EXCLUDED.parameter
            RETURNING
                post_processing_config_id
            """,
            (
                Jsonb(options.model_dump(mode="json")),
            ),
        )

        if not row:
            raise RuntimeError("Could not create post-processing config")

        return row["post_processing_config_id"]

    async def get_or_create_chunking_config_id(
        self,
        options: BaseChunkerOptions,
    ) -> int:

        row = await self.fetchone(
            """
            INSERT INTO chunking_config
            (
                parameters
            )
            VALUES (%s)
            ON CONFLICT (parameters)
            DO UPDATE SET
                parameters=EXCLUDED.parameters
            RETURNING
                chunking_config_id
            """,
            (
                Jsonb(options.model_dump(mode="json")),
            ),
        )

        if not row:
            raise RuntimeError("Could not create chunking config")

        return row["chunking_config_id"]
