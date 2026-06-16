from typing import TYPE_CHECKING, TypedDict
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from starlette.middleware.sessions import SessionMiddleware

from .endpoints import admin, auth, user
from .settings import Settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class State(TypedDict):
    db: AsyncEngine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[State]:
    engine = create_async_engine(Settings.DB_URL)

    yield {'db': engine}

    await engine.dispose()


app = FastAPI(root_path='/api', lifespan=lifespan)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(user.router)
app.add_middleware(SessionMiddleware, secret_key=Settings.SESSION_SECRET, max_age=None)
