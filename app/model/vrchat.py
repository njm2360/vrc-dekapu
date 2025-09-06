from pydantic import BaseModel
from typing import Optional


class UserInfo(BaseModel):
    id: str # ユーザーID
    state: str # 現在の状態(online or offline)
    worldId: Optional[str] = None # 現在のワールドID
    instanceId: Optional[str] = None # 現在のインスタンスID
    location: Optional[str] = None # 現在ののロケーション(wrld+instance)
    travelingToLocation: Optional[str] = None # 現在の移動先ロケーション

class GroupInstanceWorld(BaseModel):
    id: str


class GroupInstance(BaseModel):
    instanceId: str
    world: GroupInstanceWorld


class InstanceInfo(BaseModel):
    location:str
    instanceId: str
    userCount: int
    name: str
    secureName: str


class AuthVerifyResponse(BaseModel):
    verified: bool
