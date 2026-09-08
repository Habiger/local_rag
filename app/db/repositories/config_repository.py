from sqlalchemy.dialects.postgresql import insert

from app.domains.chunking.strategies.base import BaseChunkerOptions
from app.domains.post_conversion_processing.factory import PostProcessorOptions

from app.db.base_repository import BaseRepository
from app.db.models import PdfIndexingConfigModel, PostProcessingConfigModel, ChunkingConfigModel

class ConfigRepository(BaseRepository):

    async def get_or_create_pdf_indexing_config_id(
        self,
        post_processing_config_id: int,
        chunking_config_id: int,
        embedding_model: str,
    ) -> int:
        
        # 1. Create the base insert statement
        stmt = insert(PdfIndexingConfigModel).values(
            post_processing_config_id=post_processing_config_id,
            chunking_config_id=chunking_config_id,
            embedding_model=embedding_model
        )
        
        # 2. Append the ON CONFLICT DO UPDATE clause
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                'post_processing_config_id', 
                'chunking_config_id', 
                'embedding_model'
            ],
            set_={'embedding_model': stmt.excluded.embedding_model}
        ).returning(PdfIndexingConfigModel.pdf_indexing_config_id)
        
        # 3. Execute using standard SQLAlchemy async session execution
        # (Assuming your BaseRepository uses self.session as the AsyncSession)
        result = await self.session.execute(stmt)
        pdf_indexing_config_id = result.scalar_one_or_none()
        
        if pdf_indexing_config_id is None:
            raise RuntimeError("Could not create pdf_indexing_config")
            
        return pdf_indexing_config_id

    async def get_or_create_post_processing_config_id(
        self,
        options: PostProcessorOptions,
    ) -> int:

        # Extract dict from Pydantic model; SQLAlchemy's JSONB column handles the serialization
        params_dict = options.model_dump(mode="json")

        stmt = insert(PostProcessingConfigModel).values(
            parameter=params_dict
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=['parameter'],
            set_={'parameter': stmt.excluded.parameter}
        ).returning(PostProcessingConfigModel.post_processing_config_id)

        result = await self.session.execute(stmt)
        post_processing_config_id = result.scalar_one_or_none()

        if post_processing_config_id is None:
            raise RuntimeError("Could not create post-processing config")

        return post_processing_config_id

    async def get_or_create_chunking_config_id(
        self,
        options: BaseChunkerOptions,
    ) -> int:

        params_dict = options.model_dump(mode="json")

        stmt = insert(ChunkingConfigModel).values(
            parameters=params_dict
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=['parameters'],
            set_={'parameters': stmt.excluded.parameters}
        ).returning(ChunkingConfigModel.chunking_config_id)

        result = await self.session.execute(stmt)
        chunking_config_id = result.scalar_one_or_none()

        if chunking_config_id is None:
            raise RuntimeError("Could not create chunking config")

        return chunking_config_id