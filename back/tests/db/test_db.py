from typing import TYPE_CHECKING

from pytest import mark, raises
from sqlalchemy.exc import NoResultFound

from back import db

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


@mark.anyio
async def test_create_user_returns_new_user_id(db_conn: AsyncConnection):
    user_id = await db.create_user(
        db_conn,
        'created-user@example.com',
        'Created User',
        'hashed-password',
        1,
    )

    assert isinstance(user_id, int)

    user = await db.get_login_user(db_conn, 'created-user@example.com')

    assert user is not None
    assert user['id'] == user_id
    assert user['hashed_password'] == 'hashed-password'
    assert user['role_id'] == 1


@mark.anyio
async def test_create_user_returns_none_for_duplicate_mail(
    db_conn: AsyncConnection,
    student_user: dict,
):
    user_id = await db.create_user(
        db_conn,
        student_user['mail'],
        'Duplicate User',
        'hashed-password',
        1,
    )

    assert user_id is None


@mark.anyio
async def test_get_login_user_returns_none_for_unknown_mail(db_conn: AsyncConnection):
    user = await db.get_login_user(db_conn, 'missing-user@example.com')

    assert user is None


@mark.anyio
async def test_get_current_user_admin(db_conn: AsyncConnection, admin_user: dict):
    user = await db.get_current_user(db_conn, admin_user['id'])

    assert user['id'] == admin_user['id']
    assert user['mail'] == admin_user['mail']
    assert user['name'] == admin_user['name']
    assert user['role_id'] == 0
    assert user['role_title'] == 'Administrador'
    assert user['scope'] == {'global': True}


@mark.anyio
async def test_get_current_user_student_without_assists(
    db_conn: AsyncConnection,
    student_user: dict,
):
    user = await db.get_current_user(db_conn, student_user['id'])

    assert user['id'] == student_user['id']
    assert user['mail'] == student_user['mail']
    assert user['name'] == student_user['name']
    assert user['role_id'] == 1
    assert user['role_title'] == 'Aluno'
    assert user['scope'] == {'assists': []}


@mark.anyio
async def test_get_current_user_student_with_assists(
    db_conn: AsyncConnection,
    class_with_assistant: dict,
):
    assistant = class_with_assistant['assistant']
    class_ = class_with_assistant['class']

    user = await db.get_current_user(db_conn, assistant['id'])

    assert user['id'] == assistant['id']
    assert user['role_id'] == 1
    assert user['scope'] == {
        'assists': [{'id': class_['id'], 'title': class_['title']}]
    }


@mark.anyio
async def test_get_current_user_professor_with_teaches(
    db_conn: AsyncConnection,
    class_with_professor: dict,
):
    professor = class_with_professor['professor']
    class_ = class_with_professor['class']

    user = await db.get_current_user(db_conn, professor['id'])

    assert user['id'] == professor['id']
    assert user['role_id'] == 2
    assert user['role_title'] == 'Professor'
    assert user['scope'] == {
        'teaches': [{'id': class_['id'], 'title': class_['title']}]
    }


@mark.anyio
async def test_get_current_user_raises_for_unknown_user(db_conn: AsyncConnection):
    with raises(NoResultFound):
        await db.get_current_user(db_conn, 99999999)


@mark.anyio
async def test_create_auth_session_creates_active_row_and_writes_session(
    db_conn: AsyncConnection,
    student_user: dict,
):
    sess = {'stale': 'data'}

    await db.create_auth_session(
        db_conn,
        sess,
        student_user['id'],
        student_user['role_id'],
    )

    assert sess['uid'] == student_user['id']
    assert sess['rid'] == student_user['role_id']
    assert 'sid' in sess
    assert 'stale' not in sess
    assert await db.auth_session_is_active(
        db_conn,
        sess['sid'],
        student_user['id'],
    )


@mark.anyio
async def test_revoke_auth_session_makes_session_inactive(
    db_conn: AsyncConnection,
    student_user: dict,
):
    sess = {}
    await db.create_auth_session(
        db_conn,
        sess,
        student_user['id'],
        student_user['role_id'],
    )

    await db.revoke_auth_session(db_conn, sess['sid'], student_user['id'])

    assert not await db.auth_session_is_active(
        db_conn,
        sess['sid'],
        student_user['id'],
    )


@mark.anyio
async def test_auth_session_is_active_rejects_wrong_user(
    db_conn: AsyncConnection,
    student_user: dict,
    professor_user: dict,
):
    sess = {}
    await db.create_auth_session(
        db_conn,
        sess,
        student_user['id'],
        student_user['role_id'],
    )

    assert not await db.auth_session_is_active(
        db_conn,
        sess['sid'],
        professor_user['id'],
    )
