from typing import TYPE_CHECKING

from pytest import fixture

from .. import utils

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


@fixture
async def admin_user(db_conn: AsyncConnection) -> dict:
    return await utils.insert_user(db_conn, role_id=0)


@fixture
async def student_user(db_conn: AsyncConnection) -> dict:
    return await utils.insert_user(db_conn, role_id=1)


@fixture
async def professor_user(db_conn: AsyncConnection) -> dict:
    return await utils.insert_user(db_conn, role_id=2)


@fixture
async def class_row(db_conn: AsyncConnection) -> dict:
    return await utils.insert_class(db_conn)


@fixture
async def class_with_professor(
    db_conn: AsyncConnection,
    professor_user: dict,
    class_row: dict,
) -> dict:
    relation = await utils.insert_class_professor(
        db_conn,
        id=professor_user['id'],
        class_id=class_row['id'],
    )

    return {
        'professor': professor_user,
        'class': class_row,
        'relation': relation,
    }


@fixture
async def class_with_assistant(
    db_conn: AsyncConnection,
    student_user: dict,
    class_row: dict,
) -> dict:
    relation = await utils.insert_class_assistant(
        db_conn,
        id=student_user['id'],
        class_id=class_row['id'],
    )

    return {
        'assistant': student_user,
        'class': class_row,
        'relation': relation,
    }


@fixture
async def review_session(
    db_conn: AsyncConnection,
    class_row: dict,
) -> dict:
    session = await utils.insert_review_session(
        db_conn, class_id=class_row['id']
    )

    return {
        'class': class_row,
        'session': session,
    }


@fixture
async def review_session_with_assistant(
    db_conn: AsyncConnection,
    class_with_assistant: dict,
) -> dict:
    session = await utils.insert_review_session(
        db_conn,
        class_id=class_with_assistant['class']['id'],
    )
    relation = await utils.insert_session_assistant(
        db_conn,
        id=class_with_assistant['assistant']['id'],
        class_id=class_with_assistant['class']['id'],
        session_id=session['id'],
    )

    return {
        **class_with_assistant,
        'session': session,
        'session_assistant': relation,
    }


@fixture
async def review_session_with_applicant(
    db_conn: AsyncConnection,
    review_session: dict,
    student_user: dict,
) -> dict:
    application = await utils.insert_session_applicant(
        db_conn,
        id=student_user['id'],
        session_id=review_session['session']['id'],
    )

    return {
        **review_session,
        'applicant': student_user,
        'application': application,
    }


@fixture
async def review_session_with_participant(
    db_conn: AsyncConnection,
    review_session_with_applicant: dict,
) -> dict:
    participation = await utils.insert_session_participant(
        db_conn,
        id=review_session_with_applicant['applicant']['id'],
        session_id=review_session_with_applicant['session']['id'],
    )

    return {
        **review_session_with_applicant,
        'participation': participation,
    }
