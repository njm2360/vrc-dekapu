from pydantic import BaseModel
from typing import Optional


class UserInfo(BaseModel):
    id: str
    displayName: str
    worldId: Optional[str] = None
    instanceId: Optional[str] = None


class GroupInstanceWorld(BaseModel):
    id: str


class GroupInstance(BaseModel):
    instanceId: str
    world: GroupInstanceWorld


class InstanceInfo(BaseModel):
    instanceId: str
    userCount: int
    name: Optional[str] = None


class AuthVerifyResponse(BaseModel):
    verified: bool
