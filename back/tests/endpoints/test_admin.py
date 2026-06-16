from uuid import uuid4

from pytest import mark
from sqlalchemy import text


def class_payload(
    title: str,
    professor_ids: list[int] | None = None,
    assistant_ids: list[int] | None = None,
) -> dict:
    return {
        'title': title,
        'professor_ids': professor_ids or [],
        'assistant_ids': assistant_ids or [],
    }


def professor_payload(mail: str, class_ids: list[int] | None = None) -> dict:
    return {'mail': mail, 'name': 'Professor Teste', 'class_ids': class_ids or []}


@mark.anyio
async def test_non_admin_users_cannot_access_admin_endpoints(
    non_admin_test_client,
    committed_class,
):
    res_class = non_admin_test_client.post(
        '/classes',
        json=class_payload(f'admin-denied-class-{uuid4()}'),
    )
    res_list_classes = non_admin_test_client.get('/classes')
    res_professor = non_admin_test_client.post(
        '/professors',
        json=professor_payload(f'{uuid4()}@example.com'),
    )
    res_list_professors = non_admin_test_client.get('/professors')
    res_list_students = non_admin_test_client.get('/students')
    res_class_professor = non_admin_test_client.post(
        f'/classes/{committed_class["id"]}/professors',
        json={'professor_id': 1},
    )
    res_class_assistant = non_admin_test_client.post(
        f'/classes/{committed_class["id"]}/assistants',
        json={'student_id': 1},
    )

    assert res_class.status_code == 403
    assert res_list_classes.status_code == 403
    assert res_professor.status_code == 403
    assert res_list_professors.status_code == 403
    assert res_list_students.status_code == 403
    assert res_class_professor.status_code == 403
    assert res_class_assistant.status_code == 403


@mark.anyio
async def test_admin_lists_classes_with_professors(
    authed_test_client,
    db_engine,
    committed_class,
    committed_professor,
):
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                INSERT INTO class_professors(id, class_id)
                VALUES (:professor_id, :class_id);
                '''
            ),
            {
                'professor_id': committed_professor['id'],
                'class_id': committed_class['id'],
            },
        )

    res = authed_test_client.get('/classes')

    assert res.status_code == 200
    class_ = next(item for item in res.json() if item['id'] == committed_class['id'])
    assert class_['title'] == committed_class['title']
    assert class_['professors'][0]['id'] == committed_professor['id']


@mark.anyio
async def test_admin_lists_classes_with_assistants(
    authed_test_client,
    db_engine,
    committed_class,
    committed_student,
):
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                INSERT INTO class_assistants(id, class_id)
                VALUES (:student_id, :class_id);
                '''
            ),
            {
                'student_id': committed_student['id'],
                'class_id': committed_class['id'],
            },
        )

    res = authed_test_client.get('/classes')

    assert res.status_code == 200
    class_ = next(item for item in res.json() if item['id'] == committed_class['id'])
    assert class_['assistants'][0]['id'] == committed_student['id']


@mark.anyio
async def test_admin_lists_students(authed_test_client, committed_student):
    res = authed_test_client.get('/students')

    assert res.status_code == 200
    student = next(item for item in res.json() if item['id'] == committed_student['id'])
    assert student['mail'] == committed_student['mail']


@mark.anyio
async def test_admin_lists_professors_with_classes(
    authed_test_client,
    db_engine,
    committed_class,
    committed_professor,
):
    async with db_engine.begin() as conn:
        await conn.execute(
            text(
                '''
                INSERT INTO class_professors(id, class_id)
                VALUES (:professor_id, :class_id);
                '''
            ),
            {
                'professor_id': committed_professor['id'],
                'class_id': committed_class['id'],
            },
        )

    res = authed_test_client.get('/professors')

    assert res.status_code == 200
    professor = next(item for item in res.json() if item['id'] == committed_professor['id'])
    assert professor['role_id'] == 2
    assert professor['classes'][0]['id'] == committed_class['id']


@mark.anyio
async def test_admin_creates_class_without_professors(authed_test_client, db_engine):
    title = f'admin-class-empty-{uuid4()}'
    res = authed_test_client.post('/classes', json=class_payload(title))

    assert res.status_code == 201
    assert res.json()['title'] == title
    assert res.json()['professors'] == []

    async with db_engine.begin() as conn:
        created = await conn.scalar(
            text('SELECT 1 FROM classes WHERE id = :id;'),
            {'id': res.json()['id']},
        )
        await conn.execute(
            text('DELETE FROM classes WHERE id = :id;'),
            {'id': res.json()['id']},
        )

    assert created == 1


@mark.anyio
async def test_admin_creates_class_with_professor_upfront(
    authed_test_client,
    db_engine,
    committed_professor,
):
    title = f'admin-class-professor-{uuid4()}'
    res = authed_test_client.post(
        '/classes',
        json=class_payload(title, [committed_professor['id']]),
    )

    assert res.status_code == 201
    assert res.json()['professors'][0]['id'] == committed_professor['id']

    async with db_engine.begin() as conn:
        associated = await conn.scalar(
            text(
                '''
                SELECT 1
                FROM class_professors
                WHERE id = :professor_id AND class_id = :class_id;
                '''
            ),
            {'professor_id': committed_professor['id'], 'class_id': res.json()['id']},
        )
        await conn.execute(
            text('DELETE FROM class_professors WHERE class_id = :class_id;'),
            {'class_id': res.json()['id']},
        )
        await conn.execute(
            text('DELETE FROM classes WHERE id = :class_id;'),
            {'class_id': res.json()['id']},
        )

    assert associated == 1


@mark.anyio
async def test_admin_creates_class_with_assistant_upfront(
    authed_test_client,
    db_engine,
    committed_student,
):
    title = f'admin-class-assistant-{uuid4()}'
    res = authed_test_client.post(
        '/classes',
        json=class_payload(title, assistant_ids=[committed_student['id']]),
    )

    assert res.status_code == 201
    assert res.json()['assistants'][0]['id'] == committed_student['id']

    async with db_engine.begin() as conn:
        associated = await conn.scalar(
            text(
                '''
                SELECT 1
                FROM class_assistants
                WHERE id = :student_id AND class_id = :class_id;
                '''
            ),
            {'student_id': committed_student['id'], 'class_id': res.json()['id']},
        )
        await conn.execute(
            text('DELETE FROM class_assistants WHERE class_id = :class_id;'),
            {'class_id': res.json()['id']},
        )
        await conn.execute(
            text('DELETE FROM classes WHERE id = :class_id;'),
            {'class_id': res.json()['id']},
        )

    assert associated == 1


@mark.anyio
async def test_admin_creates_professor_with_classes_upfront_and_sends_email(
    authed_test_client,
    db_engine,
    committed_class,
    monkeypatch,
):
    sent: list[tuple[str, str, str]] = []

    async def fake_send_plain_mail(to: str, subject: str, body: str) -> None:
        sent.append((to, subject, body))

    monkeypatch.setattr(
        'back.endpoints.admin.mail.send_plain_mail',
        fake_send_plain_mail,
    )

    mail = f'{uuid4()}@example.com'
    res = authed_test_client.post(
        '/professors',
        json=professor_payload(mail, [committed_class['id']]),
    )

    assert res.status_code == 201
    assert res.json()['mail'] == mail
    assert res.json()['classes'][0]['id'] == committed_class['id']
    assert sent[0][0] == mail
    assert 'senha temporária' in sent[0][2]

    async with db_engine.begin() as conn:
        associated = await conn.scalar(
            text(
                '''
                SELECT 1
                FROM class_professors
                WHERE id = :professor_id AND class_id = :class_id;
                '''
            ),
            {'professor_id': res.json()['id'], 'class_id': committed_class['id']},
        )
        await conn.execute(
            text('DELETE FROM class_professors WHERE id = :professor_id;'),
            {'professor_id': res.json()['id']},
        )
        await conn.execute(
            text('DELETE FROM users WHERE id = :professor_id;'),
            {'professor_id': res.json()['id']},
        )

    assert associated == 1


@mark.anyio
async def test_create_class_rejects_non_professor_upfront(
    authed_test_client,
    db_engine,
    committed_student,
):
    title = f'admin-class-invalid-professor-{uuid4()}'
    res = authed_test_client.post(
        '/classes',
        json=class_payload(title, [committed_student['id']]),
    )

    assert res.status_code == 400

    async with db_engine.begin() as conn:
        created = await conn.scalar(
            text('SELECT 1 FROM classes WHERE title = :title;'),
            {'title': title},
        )

    assert created is None


@mark.anyio
async def test_create_professor_rejects_nonexistent_class_upfront(
    authed_test_client,
    db_engine,
    monkeypatch,
):
    sent: list[tuple[str, str, str]] = []

    async def fake_send_plain_mail(to: str, subject: str, body: str) -> None:
        sent.append((to, subject, body))

    monkeypatch.setattr(
        'back.endpoints.admin.mail.send_plain_mail',
        fake_send_plain_mail,
    )

    mail = f'{uuid4()}@example.com'
    res = authed_test_client.post('/professors', json=professor_payload(mail, [99999999]))

    assert res.status_code == 400
    assert sent == []

    async with db_engine.begin() as conn:
        created = await conn.scalar(
            text('SELECT 1 FROM users WHERE mail = :mail;'),
            {'mail': mail},
        )

    assert created is None


@mark.anyio
async def test_admin_associates_professor_to_class(
    authed_test_client,
    db_engine,
    committed_professor,
    committed_class,
):
    res = authed_test_client.post(
        f'/classes/{committed_class["id"]}/professors',
        json={'professor_id': committed_professor['id']},
    )

    assert res.status_code == 201
    assert res.json()['class_id'] == committed_class['id']
    assert res.json()['professor']['id'] == committed_professor['id']

    async with db_engine.begin() as conn:
        associated = await conn.scalar(
            text(
                '''
                SELECT 1
                FROM class_professors
                WHERE id = :professor_id AND class_id = :class_id;
                '''
            ),
            {'professor_id': committed_professor['id'], 'class_id': committed_class['id']},
        )

    assert associated == 1


@mark.anyio
async def test_class_professor_endpoint_rejects_non_professor(
    authed_test_client,
    committed_student,
    committed_class,
):
    res = authed_test_client.post(
        f'/classes/{committed_class["id"]}/professors',
        json={'professor_id': committed_student['id']},
    )

    assert res.status_code == 400


@mark.anyio
async def test_admin_associates_student_to_class_as_assistant(
    authed_test_client,
    db_engine,
    committed_student,
    committed_class,
):
    res = authed_test_client.post(
        f'/classes/{committed_class["id"]}/assistants',
        json={'student_id': committed_student['id']},
    )

    assert res.status_code == 201
    assert res.json()['class_id'] == committed_class['id']
    assert res.json()['assistant']['id'] == committed_student['id']

    async with db_engine.begin() as conn:
        associated = await conn.scalar(
            text(
                '''
                SELECT 1
                FROM class_assistants
                WHERE id = :student_id AND class_id = :class_id;
                '''
            ),
            {'student_id': committed_student['id'], 'class_id': committed_class['id']},
        )

    assert associated == 1


@mark.anyio
async def test_class_assistant_endpoint_rejects_non_student(
    authed_test_client,
    committed_professor,
    committed_class,
):
    res = authed_test_client.post(
        f'/classes/{committed_class["id"]}/assistants',
        json={'student_id': committed_professor['id']},
    )

    assert res.status_code == 400


@mark.anyio
async def test_admin_association_endpoints_reject_duplicate_associations(
    authed_test_client,
    committed_professor,
    committed_student,
    committed_class,
):
    first_professor = authed_test_client.post(
        f'/classes/{committed_class["id"]}/professors',
        json={'professor_id': committed_professor['id']},
    )
    second_professor = authed_test_client.post(
        f'/classes/{committed_class["id"]}/professors',
        json={'professor_id': committed_professor['id']},
    )
    first_assistant = authed_test_client.post(
        f'/classes/{committed_class["id"]}/assistants',
        json={'student_id': committed_student['id']},
    )
    second_assistant = authed_test_client.post(
        f'/classes/{committed_class["id"]}/assistants',
        json={'student_id': committed_student['id']},
    )

    assert first_professor.status_code == 201
    assert second_professor.status_code == 400
    assert first_assistant.status_code == 201
    assert second_assistant.status_code == 400
