import os
from typing import Annotated, TypedDict, TYPE_CHECKING
from contextlib import asynccontextmanager

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.profiles import CHEAPEST
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncConnection
)
from starlette.middleware.sessions import SessionMiddleware

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class State(TypedDict):
    db: AsyncEngine
    ph: PasswordHasher
    dummy_hash: str


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[State]:
    engine = create_async_engine(os.environ['DB_URL'])
    ph = PasswordHasher.from_parameters(CHEAPEST)
    dummy_hash = ph.hash('dummypassword')

    yield { 'db': engine, 'ph': ph, 'dummy_hash': dummy_hash }

    await engine.dispose()


async def get_db(req: Request) -> AsyncIterator[AsyncConnection]:
    async with req.state['db'].begin() as conn:
        yield conn

def get_ph(req: Request) -> tuple[PasswordHasher, str]:
    return (req.state['ph'], req.state['dummy_hash'])

async def require_session(req: Request) -> dict:
    if not req.session:
        raise HTTPException(status_code=401)

    return req.session


ConnDep = Annotated[AsyncConnection, Depends(get_db)]
SidCookieDep = Annotated[dict, Depends(require_session)]
HashToolDep = Annotated[tuple[PasswordHasher, str], Depends(get_ph)]


class LoginModel(BaseModel):
    mail: str
    password: str

LoginForm = LoginModel


app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware,
    secret_key = os.environ['SESSION_SECRET'],
    max_age = None
)


@app.post('/login', status_code=204)
async def login(
    req: Request,
    conn: ConnDep,
    hash_tool: HashToolDep,
    login_form: LoginForm,
) -> None:
    result = (await conn.execute(
        text(
            '''
            SELECT id, name, hashed_password, role_id
            FROM users
            WHERE mail = :mail;
            '''
        ).bindparams(mail=login_form.mail)
    )).first()

    hasher, dummy_hash = hash_tool
    try:
        if result is None:
            # Mantem tempo constante. Sempre lança a exception:
            await run_in_threadpool(hasher.verify, dummy_hash, '')
            raise VerifyMismatchError  # garante

        user_id, user_name, user_hpw, user_role = result
        await run_in_threadpool(hasher.verify, user_hpw, login_form.password)
    except VerifyMismatchError:
        raise HTTPException(status_code=401)

    req.session.update(id=user_id, name=user_name, role=user_role)


@app.get('/')
async def homepage(session: SidCookieDep) -> JSONResponse:
    return JSONResponse(content=session)
