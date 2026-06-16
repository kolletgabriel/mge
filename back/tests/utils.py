from base64 import b64encode
from datetime import datetime, timedelta, timezone
from json import dumps
from uuid import uuid4, UUID

from itsdangerous import TimestampSigner
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from back.settings import Settings

TEST_SESSION_ID = UUID('00000000-0000-4000-8000-000000000000')


def sign_session_data(sess_data: dict[str, int | str]) -> str:
    return TimestampSigner(str(Settings.SESSION_SECRET)).sign(
        b64encode(dumps(sess_data).encode('utf-8'))
    ).decode('utf-8')


async def insert_user(
    conn: AsyncConnection,
    *,
    role_id: int = 1,
    mail: str | None = None,
    name: str | None = None,
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO users(mail, name, hashed_password, role_id)
            VALUES (:mail, :name, 'hash', :role_id)
            RETURNING *;
            '''
        ).bindparams(
            mail = (mail or f'{uuid4()}@example.com'),
            name = (name or f'User {uuid4()}'),
            role_id = role_id
        )
    )).one()._asdict()


async def insert_class(
    conn: AsyncConnection,
    *,
    title: str | None = None,
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO classes(title)
            VALUES (:title)
            RETURNING *;
            '''
        ).bindparams(
            title = (title or f'Class {uuid4()}')
        )
    )).one()._asdict()


async def insert_class_professor(
    conn: AsyncConnection,
    *,
    id: int,
    class_id: int
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO class_professors(id, class_id)
            VALUES (:id, :class_id)
            RETURNING *;
            '''
        ).bindparams(
            id = id,
            class_id = class_id
        )
    )).one()._asdict()


async def insert_class_assistant(
    conn: AsyncConnection,
    *,
    id: int,
    class_id: int
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO class_assistants(id, class_id)
            VALUES (:id, :class_id)
            RETURNING *;
            '''
        ).bindparams(
            id = id,
            class_id = class_id
        )
    )).one()._asdict()


async def insert_review_session(
    conn: AsyncConnection,
    *,
    class_id: int,
    starts_at: datetime | None = None,
    ends_at: datetime | None = None,
    max_participants: int = 5,
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO review_sessions(
                class_id,
                starts_at,
                ends_at,
                max_participants
            )
            VALUES (:class_id, :starts_at, :ends_at, :max_participants)
            RETURNING *;
            '''
        ).bindparams(
            class_id = class_id,
            starts_at = (starts_at or datetime.now(timezone.utc)),
            ends_at = (
                ends_at or (datetime.now(timezone.utc) + timedelta(hours=1))
            ),
            max_participants = max_participants
        )
    )).one()._asdict()


async def insert_session_assistant(
    conn: AsyncConnection,
    *,
    id: int,
    class_id: int,
    session_id: int
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO session_assistants(id, class_id, session_id)
            VALUES (:id, :class_id, :session_id)
            RETURNING *;
            '''
        ).bindparams(
            id = id,
            class_id = class_id,
            session_id = session_id
        )
    )).one()._asdict()


async def insert_session_applicant(
    conn: AsyncConnection,
    *,
    id: int,
    session_id: int
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO session_applicants(id, session_id)
            VALUES (:id, :session_id)
            RETURNING *;
            '''
        ).bindparams(
            id = id,
            session_id = session_id
        )
    )).one()._asdict()


async def insert_session_participant(
    conn: AsyncConnection,
    *,
    id: int,
    session_id: int,
    attended: bool = False
) -> dict:
    return (await conn.execute(
        text(
            '''
            INSERT INTO session_participants(id, session_id, attended)
            VALUES (:id, :session_id, :attended)
            RETURNING *;
            '''
        ).bindparams(
            id = id,
            session_id = session_id,
            attended = attended
        )
    )).one()._asdict()
