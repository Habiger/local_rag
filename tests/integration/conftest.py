import os
os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import pytest
import pytest_asyncio
from collections.abc import AsyncGenerator
from unittest.mock import patch, PropertyMock
from testcontainers.postgres import PostgresContainer

# Adjust these imports to match your project structure
from app.config.settings import DBConfig
from app.db.database import db
from app.db.unit_of_work import unit_of_work, LazyWorkContext

# 1. Start the container once for the whole test session
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("pgvector/pgvector:0.8.2-pg18-trixie") as postgres:
        yield postgres

# conftest.py snippet
@pytest_asyncio.fixture(scope="function")
async def setup_database(postgres_container: PostgresContainer):
    # 1. Manually create a config object for the test
    test_config = DBConfig(
        host=postgres_container.get_container_host_ip(),
        port=str(postgres_container.get_exposed_port(5432)),
        name=postgres_container.dbname,
        user=postgres_container.username,
        password=postgres_container.password
    )

    # 2. Pass it directly to the DB setup
    await db.setup(config=test_config)
    await db.create_schema()
    
    yield db
    
    await db.drop_schema()
    await db.teardown()

# 3. Provide the Unit of Work context to your tests
@pytest_asyncio.fixture(scope="function")
async def uow(setup_database) -> AsyncGenerator[LazyWorkContext, None]:
    """
    Yields the LazyWorkContext registry for testing repositories.
    Requires `setup_database` to ensure the pool and schema exist first.
    """
    async with unit_of_work(setup_database.pool) as uow:
        yield uow
        
