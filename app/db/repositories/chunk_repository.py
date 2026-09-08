import json
from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.base_repository import BaseRepository
from app.db.models import ChunkModel, DocItemModel, ChunkDocItemMappingModel
from app.domains.chunking.strategies.base import Chunk

class ChunkRepository(BaseRepository):

    async def batch_insert(
        self,
        indexed_pdf_id: int,
        post_processing_config_id: int,
        pdf_id: int,
        chunks: list[Chunk],
    ) -> list[int]:
        if not chunks:
            return []

        # ============================================================
        # 1. INSERT CHUNKS
        # ============================================================
        chunk_dicts = [
            {
                # Using .key ensures you never hardcode a string
                ChunkModel.indexed_pdf_id.key: indexed_pdf_id,
                ChunkModel.chunk_text.key: c.text
            }
            for c in chunks
        ]

        chunk_stmt = insert(ChunkModel).values(chunk_dicts).returning(ChunkModel.chunk_id)
        chunk_result = await self.session.execute(chunk_stmt)
        chunk_ids = [row.chunk_id for row in chunk_result.all()]

        # ============================================================
        # 2. INSERT DOC ITEMS (UPSERT)
        # ============================================================
        unique_doc_items = {
            doc_item.self_ref: doc_item 
            for chunk_obj in chunks 
            for doc_item in chunk_obj.doc_items
        }

        doc_item_id_map: dict[str, int] = {}

        if unique_doc_items:
            doc_item_dicts = [
                {
                    DocItemModel.pdf_id.key: pdf_id,
                    DocItemModel.post_processing_config_id.key: post_processing_config_id,
                    DocItemModel.doc_item_ref.key: doc_item.self_ref,
                    DocItemModel.doc_item.key: json.loads(doc_item.model_dump_json()), 
                }
                for doc_item in unique_doc_items.values()
            ]

            doc_item_stmt = pg_insert(DocItemModel).values(doc_item_dicts)
            
            # Using model attributes directly for conflict resolution!
            doc_item_stmt = doc_item_stmt.on_conflict_do_update(
                index_elements=[
                    DocItemModel.pdf_id, 
                    DocItemModel.post_processing_config_id, 
                    DocItemModel.doc_item_ref
                ],
                set_={
                    DocItemModel.doc_item: doc_item_stmt.excluded.doc_item
                }
            ).returning(DocItemModel.doc_item_id, DocItemModel.doc_item_ref)

            doc_item_result = await self.session.execute(doc_item_stmt)
            for row in doc_item_result.all():
                doc_item_id_map[row.doc_item_ref] = row.doc_item_id

        # ============================================================
        # 3. BUILD MAPPINGS
        # ============================================================
        mapping_dicts = []
        for chunk_obj, chunk_id in zip(chunks, chunk_ids):
            for doc_ref in chunk_obj.contained_doc_item_strings:
                doc_item_id = doc_item_id_map.get(doc_ref)
                if doc_item_id is not None:
                    mapping_dicts.append({
                        ChunkDocItemMappingModel.chunk_id.key: chunk_id,
                        ChunkDocItemMappingModel.doc_item_id.key: doc_item_id
                    })

        # ============================================================
        # 4. INSERT MAPPINGS 
        # ============================================================
        if mapping_dicts:
            mapping_stmt = pg_insert(ChunkDocItemMappingModel).values(mapping_dicts)
            mapping_stmt = mapping_stmt.on_conflict_do_nothing()
            await self.session.execute(mapping_stmt)

        return chunk_ids