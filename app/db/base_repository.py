from typing import LiteralString

from psycopg import AsyncConnection
from psycopg.rows import dict_row

class BaseRepository:

    def __init__(self, conn: AsyncConnection):
        self.conn = conn

    async def fetchone(self, query: LiteralString, params=None):
        async with self.conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            return await cur.fetchone()

    async def fetchall(self, query: LiteralString, params=None):
        async with self.conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, params)
            return await cur.fetchall()

    async def execute(self, query: LiteralString, params=None):
        async with self.conn.cursor() as cur:
            await cur.execute(query, params)

    async def executemany(self, query: LiteralString, params_seq):
        async with self.conn.cursor() as cur:
            await cur.executemany(query, params_seq)