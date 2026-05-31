from typing import get_args

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from back.dependencies import SessionDep


router = APIRouter(dependencies=[get_args(SessionDep)[1]])


@router.get('/')
async def user_data(sess: SessionDep) -> JSONResponse:
    return JSONResponse(sess)
