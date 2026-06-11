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
from . import utils


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


@fixture
async def admin_user(db_engine: AsyncEngine) -> dict[str, int | str]:
    async with db_engine.begin() as conn:
        row = (await conn.execute(
            text(
                '''
                SELECT id, mail, name
                FROM users
                WHERE mail = 'admin@admin.com';
                '''
            )
        )).mappings().one()

    return dict(row)


@fixture
async def student_user(db_engine: AsyncEngine) -> dict[str, int | str]:
    async with db_engine.begin() as conn:
        return await utils.insert_user(conn, role_id=1)


@fixture
async def assistant_user(db_engine: AsyncEngine) -> dict[str, int | str | dict[str, int | str]]:
    async with db_engine.begin() as conn:
        user = await utils.insert_user(conn, role_id=1)
        klass = await utils.insert_class(conn)
        await conn.execute(
            text(
                '''
                INSERT INTO class_assistants(id, class_id)
                VALUES (:user_id, :class_id);
                '''
            ),
            {'user_id': user['id'], 'class_id': klass['id']},
        )

    return {**user, 'class': klass}


@fixture
async def professor_user(db_engine: AsyncEngine) -> dict[str, int | str | dict[str, int | str]]:
    async with db_engine.begin() as conn:
        user = await utils.insert_user(conn, role_id=2)
        klass = await utils.insert_class(conn)
        await conn.execute(
            text(
                '''
                INSERT INTO class_professors(id, class_id)
                VALUES (:user_id, :class_id);
                '''
            ),
            {'user_id': user['id'], 'class_id': klass['id']},
        )

    return {**user, 'class': klass}


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
