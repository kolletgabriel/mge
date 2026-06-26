from secrets import token_urlsafe
from typing import Mapping

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import SecretStr

from back import db, hash_tools, mail
from back.dependencies import AdminRequiredDep, ConnDep
from back.models import (
    AssociateAssistant,
    AssociateProfessor,
    AssistantRef,
    AssociatedAssistant,
    AssociatedProfessor,
    CreateClass,
    CreatedClass,
    CreateProfessor,
    CreatedProfessor,
)


router = APIRouter(dependencies=[AdminRequiredDep])


@router.get('/classes', response_model=list[CreatedClass])
async def list_classes(conn: ConnDep) -> list[Mapping]:
    return await db.list_created_classes(conn)


@router.post('/classes', status_code=201, response_model=CreatedClass)
async def create_class(conn: ConnDep, provided: CreateClass) -> Mapping:
    class_ = await db.create_class(conn, provided.title)
    if class_ is None:
        raise HTTPException(status_code=409)

    if not await db.associate_users_to_class(
        conn,
        'professor',
        provided.professor_ids,
        class_['id'],
    ):
        raise HTTPException(status_code=400)

    if not await db.associate_users_to_class(
        conn,
        'assistant',
        provided.assistant_ids,
        class_['id'],
    ):
        raise HTTPException(status_code=400)

    return await db.get_created_class(conn, class_['id'])


@router.get('/students', response_model=list[AssistantRef])
async def list_students(conn: ConnDep) -> list[Mapping]:
    return await db.list_students(conn)


@router.get('/professors', response_model=list[CreatedProfessor])
async def list_professors(conn: ConnDep) -> list[Mapping]:
    return await db.list_created_professors(conn)


@router.post('/professors', status_code=201, response_model=CreatedProfessor)
async def create_professor(
    conn: ConnDep,
    background_tasks: BackgroundTasks,
    provided: CreateProfessor,
) -> Mapping:
    plain_pw = token_urlsafe(12)
    hashed_pw = await hash_tools.hash_pw(SecretStr(plain_pw))
    professor_id = await db.create_user(
        conn,
        provided.mail,
        provided.name,
        hashed_pw,
        2,
    )
    if professor_id is None:
        raise HTTPException(status_code=409)

    if not await db.associate_classes_to_user(
        conn,
        'professor',
        professor_id,
        provided.class_ids,
    ):
        raise HTTPException(status_code=400)

    background_tasks.add_task(
        mail.send_plain_mail,
        provided.mail,
        'Acesso ao MGE',
        f'Olá, {provided.name}.\n\nSua senha temporária é: {plain_pw}\n',
    )

    return await db.get_created_professor_payload(conn, professor_id)


@router.post(
    '/classes/{class_id}/assistants',
    status_code=201,
    response_model=AssociatedAssistant,
)
async def associate_assistant(
    conn: ConnDep,
    class_id: int,
    provided: AssociateAssistant,
) -> Mapping:
    associated = await db.associate_users_to_class(
        conn,
        'assistant',
        [provided.student_id],
        class_id,
    )
    if not associated:
        raise HTTPException(status_code=400)

    return {
        'class_id': class_id,
        'assistant': await db.get_user_ref(conn, provided.student_id),
    }


@router.post(
    '/classes/{class_id}/professors',
    status_code=201,
    response_model=AssociatedProfessor,
)
async def associate_professor(
    conn: ConnDep,
    class_id: int,
    provided: AssociateProfessor,
) -> Mapping:
    associated = await db.associate_users_to_class(
        conn,
        'professor',
        [provided.professor_id],
        class_id,
    )
    if not associated:
        raise HTTPException(status_code=400)

    return {
        'class_id': class_id,
        'professor': await db.get_user_ref(conn, provided.professor_id),
    }
