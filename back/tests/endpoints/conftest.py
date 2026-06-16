from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi.testclient import TestClient
from pytest import fixture, mark
from sqlalchemy import text

from back import app

from .. import utils
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


@fixture
async def non_admin_test_client(
    test_client: TestClient,
    db_engine: AsyncEngine,
) -> AsyncIterator[TestClient]:
    session_id = uuid4()
    async with db_engine.begin() as conn:
        user = await utils.insert_user(conn, role_id=1)
        await conn.execute(
            text(
                '''
                INSERT INTO auth_sessions(id, user_id)
                VALUES (:sid, :uid);
                '''
            ).bindparams(sid=session_id, uid=user['id'])
        )

    test_client.cookies['session'] = sign_session_data({
        'uid': user['id'],
        'rid': user['role_id'],
        'sid': str(session_id),
    })

    yield test_client

    test_client.cookies.pop('session', None)
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                DELETE FROM auth_sessions
                WHERE id = :sid;
                '''
            ).bindparams(sid=session_id)
        )
        await conn.execute(
            text(
                '''
                DELETE FROM users
                WHERE id = :uid;
                '''
            ).bindparams(uid=user['id'])
        )


@fixture
async def committed_student(db_engine: AsyncEngine) -> AsyncIterator[dict]:
    async with db_engine.begin() as conn:
        user = await utils.insert_user(conn, role_id=1)

    yield user

    async with db_engine.begin() as conn:
        await conn.execute(text('DELETE FROM class_assistants WHERE id = :uid;').bindparams(uid=user['id']))
        await conn.execute(text('DELETE FROM session_applicants WHERE id = :uid;').bindparams(uid=user['id']))
        await conn.execute(text('DELETE FROM users WHERE id = :uid;').bindparams(uid=user['id']))


@fixture
async def committed_professor(db_engine: AsyncEngine) -> AsyncIterator[dict]:
    async with db_engine.begin() as conn:
        user = await utils.insert_user(conn, role_id=2)

    yield user

    async with db_engine.begin() as conn:
        await conn.execute(text('DELETE FROM class_professors WHERE id = :uid;').bindparams(uid=user['id']))
        await conn.execute(text('DELETE FROM users WHERE id = :uid;').bindparams(uid=user['id']))


@fixture
async def committed_class(db_engine: AsyncEngine) -> AsyncIterator[dict]:
    async with db_engine.begin() as conn:
        class_ = await utils.insert_class(conn)

    yield class_

    async with db_engine.begin() as conn:
        await conn.execute(text('DELETE FROM class_professors WHERE class_id = :cid;').bindparams(cid=class_['id']))
        await conn.execute(text('DELETE FROM class_assistants WHERE class_id = :cid;').bindparams(cid=class_['id']))
        await conn.execute(text('DELETE FROM classes WHERE id = :cid;').bindparams(cid=class_['id']))
