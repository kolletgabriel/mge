from typing import Annotated, AsyncIterator, Any

from fastapi import Depends, Request, HTTPException
from argon2 import PasswordHasher
from sqlalchemy.ext.asyncio import AsyncConnection


async def get_db(req: Request) -> AsyncIterator[AsyncConnection]:
    async with req.state['db'].begin() as conn:
        yield conn


async def get_ph(req: Request) -> tuple[PasswordHasher, str]:
    return (req.state['ph'], req.state['dummy_hash'])


async def require_session(req: Request) -> dict[str, Any]:
    if not req.session:
        raise HTTPException(status_code=401)

    return req.session


ConnDep = Annotated[AsyncConnection, Depends(get_db)]
SessionDep = Annotated[dict[str, Any], Depends(require_session)]
HashToolDep = Annotated[tuple[PasswordHasher, str], Depends(get_ph)]
