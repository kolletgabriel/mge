from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, Field, PositiveInt, SecretStr, StringConstraints, UUID4, model_validator


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
Title = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255
    )
]
Password = Annotated[SecretStr, Field(min_length=8, max_length=128)]
AssistantIds = Annotated[
    list[PositiveInt],
    AfterValidator(lambda ids: list(dict.fromkeys(ids)))
]


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


class ProfessorRef(BaseModel):
    id: PositiveInt
    mail: str
    name: str


class AssistantRef(BaseModel):
    id: PositiveInt
    mail: str
    name: str


class CreateClass(BaseModel):
    title: Title
    professor_ids: list[PositiveInt] = Field(default_factory=list)
    assistant_ids: list[PositiveInt] = Field(default_factory=list)


class CreatedClass(ClassRef):
    professors: list[ProfessorRef] = Field(default_factory=list)
    assistants: list[AssistantRef] = Field(default_factory=list)


class CreateProfessor(BaseModel):
    mail: Email
    name: Name
    class_ids: list[PositiveInt] = Field(default_factory=list)


class CreatedProfessor(ProfessorRef):
    role_id: Literal[2]
    role_title: Literal['Professor']
    classes: list[ClassRef] = Field(default_factory=list)


class AssociateAssistant(BaseModel):
    student_id: PositiveInt


class AssociatedAssistant(BaseModel):
    class_id: PositiveInt
    assistant: AssistantRef


class AssociateProfessor(BaseModel):
    professor_id: PositiveInt


class AssociatedProfessor(BaseModel):
    class_id: PositiveInt
    professor: ProfessorRef


class SchedulableClass(ClassRef):
    assistants: list[AssistantRef] = Field(default_factory=list)


class ReviewSessionRequest(BaseModel):
    class_id: PositiveInt
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    location: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ] = 'online'
    max_participants: PositiveInt = 5
    assistant_ids: AssistantIds = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_schedule_window(self) -> Self:
        if (self.starts_at is None) != (self.ends_at is None):
            raise ValueError('starts_at and ends_at must be provided together')

        if (self.starts_at is not None
                and self.ends_at is not None
                and self.ends_at <= self.starts_at):
            raise ValueError('ends_at must be after starts_at')

        return self


class ReviewSession(BaseModel):
    id: PositiveInt
    class_: ClassRef = Field(alias='class')
    starts_at: datetime | None
    ends_at: datetime | None
    location: str
    max_participants: PositiveInt
    assistants: list[AssistantRef] = Field(default_factory=list)
    scheduled: bool
    archived: bool


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
