from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, PositiveInt, SecretStr, StringConstraints, UUID4


Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=3,
        max_length=320,
        pattern=r'^[^@\s]+@[^@\s]+\.[^@\s]+$',
    ),
    AfterValidator(lambda e: e.lower())
]
Name = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=100
    )
]
Password = Annotated[SecretStr, Field(min_length=8, max_length=128)]


class Credentials(BaseModel):
    mail: Annotated[str, StringConstraints(strip_whitespace=True)]
    password: SecretStr


class Registration(BaseModel):
    mail: Email
    name: Name
    password: Password


class SessionData(BaseModel):
    uid: PositiveInt
    rid: Literal[0, 1, 2]
    sid: UUID4


class ClassRef(BaseModel):
    id: PositiveInt
    title: str


class CurrentUserBase(BaseModel):
    id: PositiveInt
    mail: str
    name: str


class AdminScope(BaseModel):
    global_: bool = Field(alias='global')


class AdminUser(CurrentUserBase):
    role_id: Literal[0]
    role_title: Literal['Administrador']
    scope: AdminScope


class StudentScope(BaseModel):
    assists: list[ClassRef] = Field(default_factory=list)


class StudentUser(CurrentUserBase):
    role_id: Literal[1]
    role_title: Literal['Aluno']
    scope: StudentScope


class ProfessorScope(BaseModel):
    teaches: list[ClassRef] = Field(default_factory=list)


class ProfessorUser(CurrentUserBase):
    role_id: Literal[2]
    role_title: Literal['Professor']
    scope: ProfessorScope


CurrentUser = Annotated[
    AdminUser | StudentUser | ProfessorUser,
    Field(discriminator='role_id'),
]
