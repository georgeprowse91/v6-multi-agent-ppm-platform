from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCIM_CORE_USER = "urn:ietf:params:scim:schemas:core:2.0:User"
SCIM_CORE_GROUP = "urn:ietf:params:scim:schemas:core:2.0:Group"
SCIM_LIST_RESPONSE = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
SCIM_PATCH = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
SCIM_EXTENSION_ROLES = "urn:ietf:params:scim:schemas:extension:ppm:2.0:User"


class Email(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    value: str
    type: str | None = None
    primary: bool | None = None


class GroupRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    value: str
    display: str | None = None


class MemberRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    value: str
    display: str | None = None


class ScimUserCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_name: str = Field(alias="userName")
    display_name: str | None = Field(default=None, alias="displayName")
    active: bool | None = True
    emails: list[Email] | None = None
    groups: list[GroupRef] | None = None


class ScimGroupCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    display_name: str = Field(alias="displayName")
    members: list[MemberRef] | None = None


class ScimUser(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schemas: list[str]
    id: str
    user_name: str = Field(alias="userName")
    display_name: str | None = Field(default=None, alias="displayName")
    active: bool | None = True
    emails: list[Email] | None = None
    groups: list[GroupRef] | None = None
    roles_extension: dict[str, Any] | None = Field(default=None, alias=SCIM_EXTENSION_ROLES)


class ScimGroup(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schemas: list[str]
    id: str
    display_name: str = Field(alias="displayName")
    members: list[MemberRef] | None = None


class ScimListResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schemas: list[str]
    total_results: int = Field(alias="totalResults")
    items_per_page: int = Field(alias="itemsPerPage")
    start_index: int = Field(alias="startIndex")
    resources: list[Any] = Field(alias="Resources")


class PatchOperation(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    op: str
    path: str | None = None
    value: Any | None = None


class PatchRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schemas: list[str] | None = None
    operations: list[PatchOperation] = Field(alias="Operations")
