from pytest import mark

from back import db


@mark.anyio
async def test_gcu_admin(db_engine, admin_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, admin_user['id'])

    assert user is not None
    assert user['id'] == admin_user['id']
    assert user['mail'] == admin_user['mail']
    assert user['name'] == admin_user['name']
    assert user['role'] == 'admin'
    assert user['rid'] == 0
    assert user['scope']['global'] is True


@mark.anyio
async def test_gcu_student_regular(db_engine, student_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, student_user['id'])

    assert user is not None
    assert user['id'] == student_user['id']
    assert user['mail'] == student_user['mail']
    assert user['name'] == student_user['name']
    assert user['role'] == 'student'
    assert user['rid'] == 1
    assert user['scope']['assistant_for'] == []


@mark.anyio
async def test_gcu_student_assistant(db_engine, assistant_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, assistant_user['id'])

    klass = assistant_user['class']

    assert user is not None
    assert user['id'] == assistant_user['id']
    assert user['mail'] == assistant_user['mail']
    assert user['name'] == assistant_user['name']
    assert user['role'] == 'student'
    assert user['rid'] == 1
    assert user['scope']['assistant_for'][0]['id'] == klass['id']
    assert user['scope']['assistant_for'][0]['title'] == klass['title']


@mark.anyio
async def test_gcu_professor(db_engine, professor_user):
    async with db_engine.begin() as conn:
        user = await db.get_current_user(conn, professor_user['id'])

    klass = professor_user['class']

    assert user is not None
    assert user['id'] == professor_user['id']
    assert user['mail'] == professor_user['mail']
    assert user['name'] == professor_user['name']
    assert user['role'] == 'professor'
    assert user['rid'] == 2
    assert user['scope']['classes'][0]['id'] == klass['id']
    assert user['scope']['classes'][0]['title'] == klass['title']
