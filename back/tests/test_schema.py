from pytest import mark
from sqlalchemy import text

from . import utils


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
            text(
                '''
                SELECT role_id
                FROM users
                WHERE mail = 'admin@admin.com';
                '''
            )
        )

    assert {
        'users',
        'auth_sessions',
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
async def test_auth_sessions_enforce_user_fk_uuid_default_and_revocation(db_engine):
    async with db_engine.begin() as conn:
        user = await utils.insert_user(conn, mail='schema-auth-session@example.com')
        row = (
            await conn.execute(
                text(
                    '''
                    INSERT INTO auth_sessions(user_id)
                    VALUES (:user_id)
                    RETURNING id, revoked_at;
                    '''
                ),
                {'user_id': user['id']},
            )
        ).one()

        assert row.id is not None
        assert row.revoked_at is None

        revoked_at = await conn.scalar(
            text(
                '''
                UPDATE auth_sessions
                SET revoked_at = '2030-01-01 10:00Z'
                WHERE id = :session_id
                RETURNING revoked_at;
                '''
            ),
            {'session_id': row.id},
        )

    assert revoked_at is not None

    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO auth_sessions(user_id) VALUES (99999999);',
    )
    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO auth_sessions(id, user_id) VALUES (:session_id, :user_id);',
        {'session_id': row.id, 'user_id': user['id']},
    )


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

    await utils.assert_integrity_error(
        db_engine,
        '''
        INSERT INTO users(mail, name, hashed_password, role_id)
        VALUES ('schema-invalid-role@example.com', 'Invalid Role', 'hash', 9);
        ''',
    )
    await utils.assert_integrity_error(
        db_engine,
        '''
        INSERT INTO users(mail, name, hashed_password)
        VALUES ('schema-default-role@example.com', 'Duplicate', 'hash');
        ''',
    )


@mark.anyio
async def test_class_professors_require_professor_users(db_engine):
    async with db_engine.begin() as conn:
        klass = await utils.insert_class(conn, title='schema-professors-class')
        professor = await utils.insert_user(conn, role_id=2, mail='schema-professor@example.com')
        student = await utils.insert_user(conn, role_id=1, mail='schema-not-professor@example.com')

        await conn.execute(
            text(
                '''
                INSERT INTO class_professors(id, class_id)
                VALUES (:id, :class_id);
                '''
            ),
            {'id': professor['id'], 'class_id': klass['id']},
        )

    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO class_professors(id, class_id) VALUES (:id, :class_id);',
        {'id': student['id'], 'class_id': klass['id']},
    )
    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO class_professors(id, class_id) VALUES (:id, :class_id);',
        {'id': professor['id'], 'class_id': klass['id']},
    )


@mark.anyio
async def test_class_assistants_require_student_users(db_engine):
    async with db_engine.begin() as conn:
        klass = await utils.insert_class(conn, title='schema-assistants-class')
        student = await utils.insert_user(conn, role_id=1, mail='schema-assistant@example.com')
        professor = await utils.insert_user(conn, role_id=2, mail='schema-not-assistant@example.com')

        await conn.execute(
            text('INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);'),
            {'id': student['id'], 'class_id': klass['id']},
        )

    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);',
        {'id': professor['id'], 'class_id': klass['id']},
    )
    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);',
        {'id': student['id'], 'class_id': klass['id']},
    )


@mark.anyio
async def test_review_sessions_enforce_foreign_key_checks_and_defaults(db_engine):
    async with db_engine.begin() as conn:
        klass = await utils.insert_class(conn, title='schema-review-session-class')
        row = (
            await conn.execute(
                text(
                    '''
                    INSERT INTO review_sessions(class_id, starts_at, ends_at)
                    VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 11:00Z')
                    RETURNING location, max_participants;
                    '''
                ),
                {'class_id': klass['id']},
            )
        ).one()

    assert row == ('online', 5)

    await utils.assert_integrity_error(
        db_engine,
        '''
        INSERT INTO review_sessions(class_id, starts_at, ends_at)
        VALUES (99999999, '2030-01-01 10:00Z', '2030-01-01 11:00Z');
        ''',
    )
    await utils.assert_integrity_error(
        db_engine,
        '''
        INSERT INTO review_sessions(class_id, starts_at, ends_at)
        VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 10:00Z');
        ''',
        {'class_id': klass['id']},
    )
    await utils.assert_integrity_error(
        db_engine,
        '''
        INSERT INTO review_sessions(class_id, starts_at, ends_at, max_participants)
        VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 11:00Z', 0);
        ''',
        {'class_id': klass['id']},
    )


@mark.anyio
async def test_session_assistants_must_assist_same_class_as_session(db_engine):
    async with db_engine.begin() as conn:
        assistant = await utils.insert_user(conn, role_id=1, mail='schema-session-assistant@example.com')
        class_a = await utils.insert_class(conn, title='schema-session-assistant-class-a')
        class_b = await utils.insert_class(conn, title='schema-session-assistant-class-b')
        session_a = await utils.insert_review_session(conn, class_a['id'])

        await conn.execute(
            text('INSERT INTO class_assistants(id, class_id) VALUES (:id, :class_id);'),
            {'id': assistant['id'], 'class_id': class_a['id']},
        )
        await conn.execute(
            text(
                '''
                INSERT INTO session_assistants(id, class_id, session_id)
                VALUES (:id, :class_id, :session_id);
                '''
            ),
            {'id': assistant['id'], 'class_id': class_a['id'], 'session_id': session_a},
        )

    await utils.assert_integrity_error(
        db_engine,
        '''
        INSERT INTO session_assistants(id, class_id, session_id)
        VALUES (:id, :class_id, :session_id);
        ''',
        {'id': assistant['id'], 'class_id': class_b['id'], 'session_id': session_a},
    )


@mark.anyio
async def test_session_applicants_require_student_users_and_unique_application(db_engine):
    async with db_engine.begin() as conn:
        klass = await utils.insert_class(conn, title='schema-applicants-class')
        session_id = await utils.insert_review_session(conn, klass['id'])
        student = await utils.insert_user(conn, role_id=1, mail='schema-applicant@example.com')
        professor = await utils.insert_user(conn, role_id=2, mail='schema-not-applicant@example.com')

        applied_at = await conn.scalar(
            text(
                '''
                INSERT INTO session_applicants(id, session_id)
                VALUES (:id, :session_id)
                RETURNING applied_at;
                '''
            ),
            {'id': student['id'], 'session_id': session_id},
        )

    assert applied_at is not None

    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO session_applicants(id, session_id) VALUES (:id, :session_id);',
        {'id': professor['id'], 'session_id': session_id},
    )
    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO session_applicants(id, session_id) VALUES (:id, :session_id);',
        {'id': student['id'], 'session_id': session_id},
    )


@mark.anyio
async def test_session_participants_require_application_and_default_attendance(db_engine):
    async with db_engine.begin() as conn:
        klass = await utils.insert_class(conn, title='schema-participants-class')
        session_id = await utils.insert_review_session(conn, klass['id'])
        applicant = await utils.insert_user(conn, role_id=1, mail='schema-participant@example.com')
        non_applicant = await utils.insert_user(conn, role_id=1, mail='schema-non-participant@example.com')

        await conn.execute(
            text('INSERT INTO session_applicants(id, session_id) VALUES (:id, :session_id);'),
            {'id': applicant['id'], 'session_id': session_id},
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
                {'id': applicant['id'], 'session_id': session_id},
            )
        ).one()

    assert row.confirmed_at is not None
    assert row.attended is False

    await utils.assert_integrity_error(
        db_engine,
        'INSERT INTO session_participants(id, session_id) VALUES (:id, :session_id);',
        {'id': non_applicant['id'], 'session_id': session_id},
    )


@mark.anyio
async def test_session_applicants_status_orders_confirmed_and_waitlisted(db_engine):
    async with db_engine.begin() as conn:
        klass = await utils.insert_class(conn, title='schema-status-class')
        session_id = await utils.insert_review_session(conn, klass['id'], max_participants=2)
        first = await utils.insert_user(conn, role_id=1, mail='schema-status-first@example.com')
        second = await utils.insert_user(conn, role_id=1, mail='schema-status-second@example.com')
        third = await utils.insert_user(conn, role_id=1, mail='schema-status-third@example.com')

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
                'first_id': first['id'],
                'second_id': second['id'],
                'third_id': third['id'],
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
        (first['id'], 1, True, None),
        (second['id'], 2, True, None),
        (third['id'], 3, False, 1),
    ]
