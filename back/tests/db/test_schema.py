from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from pytest import mark, raises
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .. import utils

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


@mark.anyio
async def test_schema_objs_exist(db_conn: AsyncConnection):
    tables = (await db_conn.execute(
        text(
            '''
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE';
            '''
        )
    )).scalars()
    views = (await db_conn.execute(
        text(
            '''
            SELECT table_name
            FROM information_schema.views
            WHERE table_schema = 'public';
            '''
        )
    )).scalars()

    assert {
        'roles',
        'users',
        'auth_sessions',
        'classes',
        'class_professors',
        'class_assistants',
        'review_sessions',
        'session_assistants',
        'session_applicants',
        'session_participants',
    } == set(tables)
    assert {
        'class_user_refs',
        'current_users',
        'review_session_refs',
        'session_applicants_status'
    } == set(views)


@mark.anyio
async def test_seeded_roles(db_conn: AsyncConnection):
    role_ids = (await db_conn.execute(
        text(
            '''
            SELECT id
            FROM roles;
            '''
        )
    )).scalars().all()
    assert len(role_ids) == 3
    assert tuple(role_ids) == (0, 1, 2)


@mark.anyio
async def test_class_professors_require_professor_and_class(
    db_conn: AsyncConnection,
    class_with_professor: dict,
    student_user: dict,
    admin_user: dict,
):
    class_ = class_with_professor['class']
    professor = class_with_professor['professor']
    relation = class_with_professor['relation']

    assert relation['id'] == professor['id']
    assert relation['class_id'] == class_['id']

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_professor(
                db_conn,
                id=professor['id'],
                class_id=class_['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_professor(
                db_conn,
                id=student_user['id'],
                class_id=class_['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_professor(
                db_conn,
                id=admin_user['id'],
                class_id=class_['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_professor(
                db_conn,
                id=professor['id'],
                class_id=99999999,
            )


@mark.anyio
async def test_class_assistants_require_student_and_class(
    db_conn: AsyncConnection,
    class_with_assistant: dict,
    professor_user: dict,
    admin_user: dict,
):
    class_ = class_with_assistant['class']
    assistant = class_with_assistant['assistant']
    relation = class_with_assistant['relation']

    assert relation['id'] == assistant['id']
    assert relation['class_id'] == class_['id']

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_assistant(
                db_conn,
                id=assistant['id'],
                class_id=class_['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_assistant(
                db_conn,
                id=professor_user['id'],
                class_id=class_['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_assistant(
                db_conn,
                id=admin_user['id'],
                class_id=class_['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_class_assistant(
                db_conn,
                id=assistant['id'],
                class_id=99999999,
            )


@mark.anyio
async def test_review_sessions_require_existing_class(
    db_conn: AsyncConnection,
    review_session: dict,
):
    class_ = review_session['class']
    session = review_session['session']

    assert session['class_id'] == class_['id']

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_review_session(db_conn, class_id=99999999)


@mark.anyio
async def test_review_sessions_enforce_valid_time_window(
    db_conn: AsyncConnection,
    class_row: dict,
):
    starts_at = datetime.now(timezone.utc)

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_review_session(
                db_conn,
                class_id=class_row['id'],
                starts_at=starts_at,
                ends_at=starts_at - timedelta(minutes=1),
            )


@mark.anyio
async def test_session_assistants_require_assistant_for_session_class(
    db_conn: AsyncConnection,
    review_session_with_assistant: dict,
    student_user: dict,
):
    class_ = review_session_with_assistant['class']
    assistant = review_session_with_assistant['assistant']
    session = review_session_with_assistant['session']
    relation = review_session_with_assistant['session_assistant']

    assert relation['id'] == assistant['id']
    assert relation['class_id'] == class_['id']
    assert relation['session_id'] == session['id']

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_assistant(
                db_conn,
                id=assistant['id'],
                class_id=class_['id'],
                session_id=session['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_assistant(
                db_conn,
                id=student_user['id'],
                class_id=class_['id'],
                session_id=session['id'],
            )

    other_class = await utils.insert_class(db_conn)
    other_session = await utils.insert_review_session(
        db_conn,
        class_id=other_class['id'],
    )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_assistant(
                db_conn,
                id=assistant['id'],
                class_id=class_['id'],
                session_id=other_session['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_assistant(
                db_conn,
                id=assistant['id'],
                class_id=99999999,
                session_id=session['id'],
            )


@mark.anyio
async def test_session_applicants_require_student_and_session(
    db_conn: AsyncConnection,
    review_session_with_applicant: dict,
    professor_user: dict,
    admin_user: dict,
):
    session = review_session_with_applicant['session']
    applicant = review_session_with_applicant['applicant']
    application = review_session_with_applicant['application']

    assert application['id'] == applicant['id']
    assert application['session_id'] == session['id']

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_applicant(
                db_conn,
                id=applicant['id'],
                session_id=session['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_applicant(
                db_conn,
                id=professor_user['id'],
                session_id=session['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_applicant(
                db_conn,
                id=admin_user['id'],
                session_id=session['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_applicant(
                db_conn,
                id=applicant['id'],
                session_id=99999999,
            )


@mark.anyio
async def test_session_participants_require_existing_application(
    db_conn: AsyncConnection,
    review_session_with_participant: dict,
    student_user: dict,
):
    session = review_session_with_participant['session']
    applicant = review_session_with_participant['applicant']
    participation = review_session_with_participant['participation']

    assert participation['id'] == applicant['id']
    assert participation['session_id'] == session['id']

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_participant(
                db_conn,
                id=applicant['id'],
                session_id=session['id'],
            )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_participant(
                db_conn,
                id=student_user['id'],
                session_id=session['id'],
            )

    other_session = await utils.insert_review_session(
        db_conn,
        class_id=review_session_with_participant['class']['id'],
    )

    with raises(IntegrityError):
        async with db_conn.begin_nested():
            await utils.insert_session_participant(
                db_conn,
                id=applicant['id'],
                session_id=other_session['id'],
            )
