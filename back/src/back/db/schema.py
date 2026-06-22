from typing import Any, Literal, Mapping, Sequence

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    MetaData,
    SmallInteger,
    Table,
    Text,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID


metadata = MetaData()

roles = Table(
    'roles',
    metadata,
    Column('id', SmallInteger(), primary_key=True),
    Column('title', Text()),
)
users = Table(
    'users',
    metadata,
    Column('id', BigInteger(), primary_key=True),
    Column('mail', Text()),
    Column('name', Text()),
    Column('hashed_password', Text()),
    Column('role_id', SmallInteger()),
)
auth_sessions = Table(
    'auth_sessions',
    metadata,
    Column('id', PG_UUID(as_uuid=True), primary_key=True),
    Column('user_id', BigInteger()),
    Column('revoked_at', DateTime(timezone=True)),
)
classes = Table(
    'classes',
    metadata,
    Column('id', BigInteger(), primary_key=True),
    Column('title', Text()),
)
class_professors = Table(
    'class_professors',
    metadata,
    Column('id', BigInteger(), primary_key=True),
    Column('role_id', SmallInteger()),
    Column('class_id', BigInteger(), primary_key=True),
)
class_assistants = Table(
    'class_assistants',
    metadata,
    Column('id', BigInteger(), primary_key=True),
    Column('role_id', SmallInteger()),
    Column('class_id', BigInteger(), primary_key=True),
)
current_users = Table(
    'current_users',
    metadata,
    Column('id', BigInteger()),
    Column('name', Text()),
    Column('mail', Text()),
    Column('role_id', SmallInteger()),
    Column('role_title', Text()),
    Column('scope', JSONB()),
)
class_user_refs = Table(
    'class_user_refs',
    metadata,
    Column('class_id', BigInteger()),
    Column('class_title', Text()),
    Column('user_id', BigInteger()),
    Column('mail', Text()),
    Column('name', Text()),
    Column('role_id', SmallInteger()),
    Column('role_title', Text()),
)


def class_user_ref_select(class_id: int, role_id: Literal[1, 2]):
    refs = class_user_refs.c

    return (
        select(
            refs.user_id.label('id'),
            refs.mail,
            refs.name,
        ).where(
            (refs.class_id == class_id)
            & (refs.role_id == role_id)
        ).order_by(
            refs.name,
            refs.user_id
        )
    )


def created_classes_select(class_id: int | None = None):
    refs = class_user_refs.c
    stmt = (
        select(
            classes.c.id,
            classes.c.title,
            refs.user_id,
            refs.mail,
            refs.name,
            refs.role_id,
        ).select_from(
            classes.outerjoin(
                class_user_refs, (refs.class_id == classes.c.id)
            )
        ).order_by(
            classes.c.title,
            classes.c.id,
            refs.name,
            refs.user_id
        )
    )

    if class_id is not None:
        stmt = stmt.where(classes.c.id == class_id)

    return stmt


def created_classes_from_rows(
    rows: Sequence[Mapping]
) -> list[dict[str, Any]]:
    by_class: dict[int, dict[str, Any]] = {}

    for row in rows:
        class_ = by_class.setdefault(
            row['id'],
            {
                'id': row['id'],
                'title': row['title'],
                'professors': [],
                'assistants': [],
            },
        )
        if row['user_id'] is None:
            continue

        user = {'id': row['user_id'], 'mail': row['mail'], 'name': row['name']}
        if row['role_id'] == 2:
            class_['professors'].append(user)
        else:
            class_['assistants'].append(user)

    return list(by_class.values())


def created_professors_select(professor_id: int | None = None):
    refs = class_user_refs.c
    stmt = (
        select(
            users.c.id,
            users.c.mail,
            users.c.name,
            users.c.role_id,
            roles.c.title.label('role_title'),
            refs.class_id,
            refs.class_title,
        ).select_from(
            users.join(
                roles, (roles.c.id == users.c.role_id)
            ).outerjoin(
                class_user_refs,
                ((refs.user_id == users.c.id) & (refs.role_id == 2))
            )
        ).where(
            users.c.role_id == 2
        ).order_by(
            users.c.name,
            users.c.id,
            refs.class_title,
            refs.class_id
        )
    )

    if professor_id is not None:
        stmt = stmt.where(users.c.id == professor_id)

    return stmt


def created_professors_from_rows(
    rows: Sequence[Mapping]
) -> list[dict[str, Any]]:
    by_professor: dict[int, dict[str, Any]] = {}

    for row in rows:
        professor = by_professor.setdefault(
            row['id'],
            {
                'id': row['id'],
                'mail': row['mail'],
                'name': row['name'],
                'role_id': row['role_id'],
                'role_title': row['role_title'],
                'classes': [],
            },
        )
        if row['class_id'] is not None:
            professor['classes'].append({
                'id': row['class_id'],
                'title': row['class_title'],
            })

    return list(by_professor.values())
