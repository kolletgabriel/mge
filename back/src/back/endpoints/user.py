from fastapi import APIRouter
from fastapi.responses import JSONResponse

from back.dependencies import CurrentSessionDep, SessionRequiredDep


router = APIRouter(dependencies=[SessionRequiredDep])


@router.get('/')
async def user_data(sess: CurrentSessionDep) -> JSONResponse:
    return JSONResponse(sess.model_dump(mode='json'))
