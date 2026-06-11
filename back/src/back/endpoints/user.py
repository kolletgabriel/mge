from fastapi import APIRouter

from back.dependencies import CurrentUserDep
from back.models import CurrentUser


router = APIRouter()


@router.get('/me')
async def user_data(user: CurrentUserDep) -> CurrentUser:
    return user
