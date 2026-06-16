from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
from pytest import fixture, mark
from sqlalchemy import text

from back import app

from ..utils import sign_session_data, TEST_SESSION_ID

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator
    from sqlalchemy.ext.asyncio import AsyncEngine


@fixture
def test_client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c

        c.cookies.clear()


@fixture
def signed_session_token() -> str:
    return sign_session_data({'uid': 1, 'rid': 0, 'sid': str(TEST_SESSION_ID)})


@fixture
def signed_malformed_session_token() -> str:
    return sign_session_data({'uid': 1, 'rid': 0})


@fixture
async def valid_auth_session(db_engine: AsyncEngine) -> AsyncIterator[None]:
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                INSERT INTO auth_sessions(id, user_id)
                VALUES (:sid, 1);
                '''
            ).bindparams(sid=TEST_SESSION_ID)
        )

    yield

    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                DELETE FROM auth_sessions
                WHERE id = :sid;
                '''
            ).bindparams(sid=TEST_SESSION_ID)
        )


@fixture
async def revoked_auth_session(db_engine: AsyncEngine) -> AsyncIterator[None]:
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                INSERT INTO auth_sessions(id, user_id, revoked_at)
                VALUES (:sid, 1, now());
                '''
            ).bindparams(sid=TEST_SESSION_ID)
        )

    yield

    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                DELETE FROM auth_sessions
                WHERE id = :sid;
                '''
            ).bindparams(sid=TEST_SESSION_ID)
        )


@fixture
async def authed_test_client(
    test_client: TestClient,
    signed_session_token: str,
    valid_auth_session: None
) -> AsyncIterator[TestClient]:
    _ = valid_auth_session
    test_client.cookies['session'] = signed_session_token

    yield test_client

    test_client.cookies.pop('session', None)
