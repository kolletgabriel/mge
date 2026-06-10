from base64 import b64encode
from collections.abc import AsyncIterator, Iterator
from json import dumps
from pathlib import Path

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from pytest import fixture
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from testcontainers.postgres import PostgresContainer

from back import app, Settings


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


@fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(Settings.DB_URL)

    yield engine

    await engine.dispose()


@fixture(scope='session')
def test_client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


@fixture
async def signed_session_token(db_engine: AsyncEngine) -> str:
    sess_data: dict[str, int | str] = {'uid': 1, 'rid': 0}
    async with db_engine.begin() as conn:
        sid = (await conn.execute(
            text(
                '''
                INSERT INTO auth_sessions
                VALUES(DEFAULT, :uid)
                RETURNING id;
                '''
            ).bindparams(uid=sess_data['uid'])
        )).scalar()

    sess_data.update({'sid': str(sid)})

    return TimestampSigner(str(Settings.SESSION_SECRET)).sign(
        b64encode(dumps(sess_data).encode('utf-8'))
    ).decode('utf-8')


@fixture
def authed_test_client(
    test_client,
    signed_session_token
) -> Iterator[TestClient]:
    test_client.cookies['session'] = signed_session_token

    yield test_client

    del test_client.cookies['session']
