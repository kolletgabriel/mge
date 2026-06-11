from fastapi import HTTPException
from pytest import mark, raises

from back import db
from back.models import AdminUser, ProfessorUser, StudentUser


@mark.anyio
async def test_get_current_user_admin(db_engine, admin_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, admin_user['id'])

    assert isinstance(user, AdminUser)
    assert user.id == admin_user['id']
    assert user.mail == admin_user['mail']
    assert user.name == admin_user['name']
    assert user.role == 'admin'
    assert user.rid == 0
    assert user.scope.global_ is True


@mark.anyio
async def test_get_current_user_student_without_assistant_scope(db_engine, student_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, student_user['id'])

    assert isinstance(user, StudentUser)
    assert user.id == student_user['id']
    assert user.mail == student_user['mail']
    assert user.name == student_user['name']
    assert user.role == 'student'
    assert user.rid == 1
    assert user.scope.assistant_for == []


@mark.anyio
async def test_get_current_user_student_with_assistant_scope(db_engine, assistant_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, assistant_user['id'])

    klass = assistant_user['class']

    assert isinstance(user, StudentUser)
    assert user.id == assistant_user['id']
    assert user.mail == assistant_user['mail']
    assert user.name == assistant_user['name']
    assert user.role == 'student'
    assert user.rid == 1
    assert user.scope.assistant_for[0].id == klass['id']
    assert user.scope.assistant_for[0].title == klass['title']


@mark.anyio
async def test_get_current_user_professor(db_engine, professor_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, professor_user['id'])

    klass = professor_user['class']

    assert isinstance(user, ProfessorUser)
    assert user.id == professor_user['id']
    assert user.mail == professor_user['mail']
    assert user.name == professor_user['name']
    assert user.role == 'professor'
    assert user.rid == 2
    assert user.scope.classes[0].id == klass['id']
    assert user.scope.classes[0].title == klass['title']


@mark.anyio
async def test_get_current_user_failure_nonexistent_user(db_engine):
    async with db_engine.begin() as conn:
        with raises(HTTPException) as exc:
            await db.get_current_user(conn, 99999999)

    assert exc.value.status_code == 401
