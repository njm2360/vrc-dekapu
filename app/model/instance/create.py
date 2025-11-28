from typing import Optional
from pydantic import BaseModel, Field

from app.model.instance.content_settings import ContentSettings
from app.model.region import Region
from app.model.vrchat import GroupAccessType, InstanceType


class CreateInstanceConfig(BaseModel):
    world_id: str = Field(..., serialization_alias="worldId")
    type: InstanceType = Field(..., serialization_alias="type")
    region: Optional[Region] = Field(None, serialization_alias="region")
    owner_id: Optional[str] = Field(None, serialization_alias="ownerId")
    role_ids: Optional[list[str]] = Field(None, serialization_alias="roleIds")
    group_access_type: Optional[GroupAccessType] = Field(
        None, serialization_alias="groupAccessType"
    )
    queue_enabled: Optional[bool] = Field(None, serialization_alias="queueEnabled")
    display_name: Optional[str] = Field(None, serialization_alias="displayName")
    content_settings: Optional[ContentSettings] = Field(
        None, serialization_alias="contentSettings"
    )
