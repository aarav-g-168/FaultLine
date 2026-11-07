from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Email = Annotated[EmailStr, StringConstraints(max_length=254)]
Password = Annotated[str, StringConstraints(min_length=12, max_length=128)]
WorkspaceRole = Literal['admin', 'member']
ProjectRole = Literal['viewer', 'investigator', 'maintainer']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Registration(StrictModel):
    email: Email
    password: Password
    name: Name


class Login(StrictModel):
    email: Email
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]


class Refresh(StrictModel):
    refresh_token: Annotated[str, StringConstraints(min_length=32, max_length=256)]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    email: str
    name: str


class Tokens(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal['bearer'] = 'bearer'
    expires_in: int
    user: UserOut


class Named(StrictModel):
    name: Name


class WorkspaceOut(BaseModel):
    id: str
    name: str
    role: Literal['owner', 'admin', 'member']


class ProjectOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    role: ProjectRole


class EnvironmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    project_id: str
    name: str


class MemberInput(StrictModel):
    email: Email
    role: WorkspaceRole = 'member'


class MemberOut(BaseModel):
    user_id: str
    name: str
    email: str
    role: str


class GrantInput(StrictModel):
    role: ProjectRole


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    actor_id: str
    action: str
    target_id: str
    created_at: int
