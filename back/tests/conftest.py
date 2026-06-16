from pathlib import Path
from typing import TYPE_CHECKING

from pytest import fixture
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncConnection
)
from testcontainers.postgres import PostgresContainer

from back import Settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@fixture(scope='session', autouse=True)
def init_test_db():
    with (
        PostgresContainer('postgres:18.3-trixie', driver='asyncpg')
            .with_volume_mapping(
                host=str(Path(__file__).parent.parent.parent / 'init.sql'),
                container='/docker-entrypoint-initdb.d/init.sql'
            )
    ) as pg:
        Settings.DB_URL = pg.get_connection_url()

        yield


@fixture(scope='module')
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(Settings.DB_URL)

    yield engine

    await engine.dispose()


@fixture
async def db_conn(db_engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    async with db_engine.connect() as conn:
        await conn.begin()

        yield conn

        await conn.rollback()
