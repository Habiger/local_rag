from psycopg.types.json import Jsonb

from app.db.base_repository import BaseRepository

from app.schema.enums import EmbeddingTaskStatus

from app.domains.chunking.strategies.base import Chunk

class ChunkRepository(BaseRepository):

    async def batch_insert(
        self,
        indexed_pdf_id: int,
        post_processing_config_id: int,
        pdf_name: str,
        chunks: list[Chunk],
    ) -> list[int]:
        """
        Batch inserts chunks + doc_items + mappings efficiently.
        """
        if not chunks:
            return []

        # We use a raw cursor here specifically because we need to use 
        # RETURNING clauses, which execute/executemany helpers don't return cleanly.
        async with self.conn.cursor() as cur:
            
            # ============================================================
            # 1. INSERT CHUNKS
            # ============================================================
            chunk_rows = [
                (indexed_pdf_id, c.text)
                for c in chunks
            ]

            await cur.executemany(
                """
                INSERT INTO chunk (indexed_pdf_id, chunk_text)
                VALUES (%s, %s)
                RETURNING chunk_id
                """,
                chunk_rows,
            )
            
            # Default psycopg cursor returns tuples, so chunk_id is at index 0
            chunk_ids = [row[0] for row in await cur.fetchall()]

            # ============================================================
            # 2. INSERT DOC ITEMS
            # ============================================================
            doc_item_id_map: dict[str, int] = {}
            
            unique_doc_items = {
                doc_item.self_ref: doc_item 
                for chunk_obj in chunks 
                for doc_item in chunk_obj.doc_items
            }

            for doc_item in unique_doc_items.values():
                await cur.execute(
                    """
                    INSERT INTO doc_item (
                        pdf_name, post_processing_config_id, doc_item_ref, doc_item
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (pdf_name, post_processing_config_id, doc_item_ref)
                    DO UPDATE SET doc_item = EXCLUDED.doc_item
                    RETURNING doc_item_id, doc_item_ref
                    """,
                    (
                        pdf_name,
                        post_processing_config_id,
                        doc_item.self_ref,
                        Jsonb(doc_item.model_dump_json()), 
                    ),
                )

                row = await cur.fetchone()
                if row:
                    # Default tuple row: index 0 is doc_item_id, index 1 is doc_item_ref
                    doc_item_id_map[row[1]] = row[0] 

            # ============================================================
            # 3. BUILD MAPPINGS
            # ============================================================
            mapping_rows = []
            for chunk_obj, chunk_id in zip(chunks, chunk_ids):
                for doc_ref in chunk_obj.contained_doc_item_strings:
                    doc_item_id = doc_item_id_map.get(doc_ref)
                    if doc_item_id is not None:
                        mapping_rows.append((chunk_id, doc_item_id))

            # ============================================================
            # 4. INSERT MAPPINGS 
            # ============================================================
            if mapping_rows:
                # Corrected to use `cur.executemany` inside the open transaction 
                await cur.executemany(
                    """
                    INSERT INTO chunk_doc_item_mapping (chunk_id, doc_item_id)
                    VALUES (%s, %s)
                    ON CONFLICT DO NOTHING
                    """,
                    mapping_rows,
                )

        return chunk_ids
    