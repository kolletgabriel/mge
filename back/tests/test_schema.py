from collections.abc import AsyncIterator

from pytest import fixture, mark, raises
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncConnection, AsyncEngine

from back import Settings


@fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(Settings.DB_URL)

    yield engine

    await engine.dispose()


async def insert_user(conn: AsyncConnection, mail: str, role_id: int = 1) -> int:
    return await conn.scalar(
        text(
            '''
            INSERT INTO users(mail, name, hashed_password, role_id)
            VALUES (:mail, :name, 'hash', :role_id)
            RETURNING id;
            '''
        ),
        {'mail': mail, 'name': mail, 'role_id': role_id},
    )


async def insert_class(conn: AsyncConnection, title: str) -> int:
    return await conn.scalar(
        text(
            '''
            INSERT INTO classes(title)
            VALUES (:title)
            RETURNING id;
            '''
        ),
        {'title': title},
    )


async def insert_review_session(
    conn: AsyncConnection,
    class_id: int,
    *,
    max_participants: int = 5,
) -> int:
    return await conn.scalar(
        text(
            '''
            INSERT INTO review_sessions(class_id, starts_at, ends_at, max_participants)
            VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 11:00Z', :max_participants)
            RETURNING id;
            '''
        ),
        {'class_id': class_id, 'max_participants': max_participants},
    )


async def assert_integrity_error(engine: AsyncEngine, statement: str, params: dict | None = None) -> None:
    with raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(text(statement), params or {})


@mark.anyio
async def test_seed_admin_and_schema_objects_exist(db_engine):
    async with db_engine.begin() as conn:
        tables = set(
            await conn.scalars(
                text(
                    '''
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                        AND table_type = 'BASE TABLE';
                    '''
                )
            )
        )
        views = set(
            await conn.scalars(
                text(
                    '''
                    SELECT table_name
                    FROM information_schema.views
                    WHERE table_schema = 'public';
                    '''
                )
            )
        )
        admin_role = await conn.scalar(
            text("SELECT role_id FROM users WHERE mail = 'admin@admin.com';")
        )

    assert {
        'users',
        'classes',
        'class_professors',
        'class_assistants',
        'review_sessions',
        'session_assistants',
        'session_applicants',
        'session_participants',
    } <= tables
    assert 'session_applicants_status' in views
    assert admin_role == 0


@mark.anyio
async def test_user_role_defaults_check_and_unique_mail(db_engine):
    async with db_engine.begin() as conn:
        role_id = await conn.scalar(
            text(
                '''
                INSERT INTO users(mail, name, hashed_password)
                VALUES ('schema-default-role@example.com', 'Default Role', 'hash')
                RETURNING role_id;
                '''
            )
        )

    assert role_id == 1

    await assert_integrity_error(
        db_engine,
        '''
        INSERT INTO users(mail, name, hashed_password, role_id)
        VALUES ('schema-invalid-role@example.com', 'Invalid Role', 'hash', 9);
        ''',
    )
    await assert_integrity_error(
        db_engine,
        '''
        INSERT INTO users(mail, name, hashed_password)
        VALUES ('schema-default-role@example.com', 'Duplicate', 'hash');
        ''',
    )


@mark.anyio
async def test_class_professors_require_professor_users(db_engine):
    async with db_engine.begin() as conn:
        class_id = await insert_class(conn, 'schema-professors-class')
        professor_id = await insert_user(conn, 'schema-professor@example.com', role_id=2)
        student_id = await insert_user(conn, 'schema-not-professor@example.com', role_id=1)

        await conn.execute(
            text('INSERT INTO class_professors(id, class_id) VALUES (:id, :class_id);'),
            {'id': professor_id, 'class_id': class_id},
        )

    await assert_integrity_error(
        db_engine,
        'INSERT INTO class_professors(id, class_id) VALUES (:id, :class_id);',
        {'id': student_id, 'class_id': class_id},
    )
    await assert_integrity_error(
        db_engine,
        'INSERT INTO class_professors(id, class_id) VALUES (:id, :class_id);',
        {'id': professor_id, 'class_id': class_id},
    )


@mark.anyio
async def test_class_assistants_require_student_users(db_engine):
    async with db_engine.begin() as conn:
        class_id = await insert_class(conn, 'schema-assistants-class')
        student_id = await insert_user(conn, 'schema-assistant@example.com', role_id=1)
        professor_id = await insert_user(conn, 'schema-not-assistant@example.com', role_id=2)

        await conn.execute(
            text('INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);'),
            {'id': student_id, 'class_id': class_id},
        )

    await assert_integrity_error(
        db_engine,
        'INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);',
        {'id': professor_id, 'class_id': class_id},
    )
    await assert_integrity_error(
        db_engine,
        'INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);',
        {'id': student_id, 'class_id': class_id},
    )


@mark.anyio
async def test_review_sessions_enforce_foreign_key_checks_and_defaults(db_engine):
    async with db_engine.begin() as conn:
        class_id = await insert_class(conn, 'schema-review-session-class')
        row = (
            await conn.execute(
                text(
                    '''
                    INSERT INTO review_sessions(class_id, starts_at, ends_at)
                    VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 11:00Z')
                    RETURNING location, max_participants;
                    '''
                ),
                {'class_id': class_id},
            )
        ).one()

    assert row == ('online', 5)

    await assert_integrity_error(
        db_engine,
        '''
        INSERT INTO review_sessions(class_id, starts_at, ends_at)
        VALUES (99999999, '2030-01-01 10:00Z', '2030-01-01 11:00Z');
        ''',
    )
    await assert_integrity_error(
        db_engine,
        '''
        INSERT INTO review_sessions(class_id, starts_at, ends_at)
        VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 10:00Z');
        ''',
        {'class_id': class_id},
    )
    await assert_integrity_error(
        db_engine,
        '''
        INSERT INTO review_sessions(class_id, starts_at, ends_at, max_participants)
        VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 11:00Z', 0);
        ''',
        {'class_id': class_id},
    )


@mark.anyio
async def test_session_assistants_must_assist_same_class_as_session(db_engine):
    async with db_engine.begin() as conn:
        assistant_id = await insert_user(conn, 'schema-session-assistant@example.com', role_id=1)
        class_a = await insert_class(conn, 'schema-session-assistant-class-a')
        class_b = await insert_class(conn, 'schema-session-assistant-class-b')
        session_a = await insert_review_session(conn, class_a)

        await conn.execute(
            text('INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);'),
            {'id': assistant_id, 'class_id': class_a},
        )
        await conn.execute(
            text(
                '''
                INSERT INTO session_assistants(id, class_id, session_id)
                VALUES (:id, :class_id, :session_id);
                '''
            ),
            {'id': assistant_id, 'class_id': class_a, 'session_id': session_a},
        )

    await assert_integrity_error(
        db_engine,
        '''
        INSERT INTO session_assistants(id, class_id, session_id)
        VALUES (:id, :class_id, :session_id);
        ''',
        {'id': assistant_id, 'class_id': class_b, 'session_id': session_a},
    )


@mark.anyio
async def test_session_applicants_require_student_users_and_unique_application(db_engine):
    async with db_engine.begin() as conn:
        class_id = await insert_class(conn, 'schema-applicants-class')
        session_id = await insert_review_session(conn, class_id)
        student_id = await insert_user(conn, 'schema-applicant@example.com', role_id=1)
        professor_id = await insert_user(conn, 'schema-not-applicant@example.com', role_id=2)

        applied_at = await conn.scalar(
            text(
                '''
                INSERT INTO session_applicants(id, session_id)
                VALUES (:id, :session_id)
                RETURNING applied_at;
                '''
            ),
            {'id': student_id, 'session_id': session_id},
        )

    assert applied_at is not None

    await assert_integrity_error(
        db_engine,
        'INSERT INTO session_applicants(id, session_id) VALUES (:id, :session_id);',
        {'id': professor_id, 'session_id': session_id},
    )
    await assert_integrity_error(
        db_engine,
        'INSERT INTO session_applicants(id, session_id) VALUES (:id, :session_id);',
        {'id': student_id, 'session_id': session_id},
    )


@mark.anyio
async def test_session_participants_require_application_and_default_attendance(db_engine):
    async with db_engine.begin() as conn:
        class_id = await insert_class(conn, 'schema-participants-class')
        session_id = await insert_review_session(conn, class_id)
        applicant_id = await insert_user(conn, 'schema-participant@example.com', role_id=1)
        non_applicant_id = await insert_user(conn, 'schema-non-participant@example.com', role_id=1)

        await conn.execute(
            text('INSERT INTO session_applicants(id, session_id) VALUES (:id, :session_id);'),
            {'id': applicant_id, 'session_id': session_id},
        )
        row = (
            await conn.execute(
                text(
                    '''
                    INSERT INTO session_participants(id, session_id)
                    VALUES (:id, :session_id)
                    RETURNING confirmed_at, attended;
                    '''
                ),
                {'id': applicant_id, 'session_id': session_id},
            )
        ).one()

    assert row.confirmed_at is not None
    assert row.attended is False

    await assert_integrity_error(
        db_engine,
        'INSERT INTO session_participants(id, session_id) VALUES (:id, :session_id);',
        {'id': non_applicant_id, 'session_id': session_id},
    )


@mark.anyio
async def test_session_applicants_status_orders_confirmed_and_waitlisted(db_engine):
    async with db_engine.begin() as conn:
        class_id = await insert_class(conn, 'schema-status-class')
        session_id = await insert_review_session(conn, class_id, max_participants=2)
        first_id = await insert_user(conn, 'schema-status-first@example.com', role_id=1)
        second_id = await insert_user(conn, 'schema-status-second@example.com', role_id=1)
        third_id = await insert_user(conn, 'schema-status-third@example.com', role_id=1)

        await conn.execute(
            text(
                '''
                INSERT INTO session_applicants(id, session_id, applied_at)
                VALUES
                    (:third_id, :session_id, '2030-01-01 10:02Z'),
                    (:second_id, :session_id, '2030-01-01 10:00Z'),
                    (:first_id, :session_id, '2030-01-01 10:00Z');
                '''
            ),
            {
                'first_id': first_id,
                'second_id': second_id,
                'third_id': third_id,
                'session_id': session_id,
            },
        )
        rows = (
            await conn.execute(
                text(
                    '''
                    SELECT user_id, application_position, is_confirmed, waitlist_position
                    FROM session_applicants_status
                    WHERE session_id = :session_id
                    ORDER BY application_position;
                    '''
                ),
                {'session_id': session_id},
            )
        ).all()

    assert rows == [
        (first_id, 1, True, None),
        (second_id, 2, True, None),
        (third_id, 3, False, 1),
    ]
