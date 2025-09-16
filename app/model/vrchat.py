from datetime import datetime
from enum import Enum
from pydantic import BaseModel, field_validator
from typing import Optional
from pydantic import Field


class UserState(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    ACTIVE = "active"


class ReleaseStatus(Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    HIDDEN = "hidden"
    ALL = "all"


class InstanceType(Enum):
    PUBLIC = "public"
    HIDDEN = "hidden"
    FRIENDS = "friends"
    PRIVATE = "private"
    GROUP = "group"


class GroupInstanceType(Enum):
    PUBLIC = "public"
    PLUS = "plus"
    MEMBER = "members"


class InstanceEntry(BaseModel):
    instance_id: str
    user_count: int

    @classmethod
    def from_list(cls, v: list):
        if not isinstance(v, list) or len(v) != 2:
            raise ValueError("Instance entry must be [instance_id, user_count]")
        return cls(instance_id=v[0], user_count=v[1])


class UserInfo(BaseModel):
    id: str  # ユーザーID
    username: str  # ユーザー名
    display_name: str = Field(..., alias="displayName")  # 表示名
    state: UserState  # 現在の状態
    world_id: Optional[str] = Field(None, alias="worldId")  # 現在のワールドID
    instance_id: Optional[str] = Field(None, alias="instanceId")  # 現在のインスタンスID
    location: Optional[str] = None  # 現在ののロケーション(wrld+instance)
    traveling_to_instance: Optional[str] = Field(
        None, alias="travelingToInstance"
    )  # 移動先インスタンス
    traveling_to_location: Optional[str] = Field(
        None, alias="travelingToLocation"
    )  # 移動先ロケーション
    traveling_to_world: Optional[str] = Field(
        None, alias="travelingToWorld"
    )  # 移動先ワールド

    @field_validator(
        "traveling_to_instance",
        "traveling_to_location",
        "traveling_to_world",
        "instance_id",
        "location",
        "world_id",
        mode="before",
    )
    @classmethod
    def empty_or_offline_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and (v.strip() == "" or v.strip().lower() == "offline"):
            return None
        return v


class WorldInfo(BaseModel):
    id: str  # ワールドID
    name: str  # ワールド名
    description: str  # ワールド説明
    author_id: str = Field(..., alias="authorId")  # 作者のユーザーID
    author_name: str = Field(..., alias="authorName")  # 作者のユーザー名
    capacity: int  # 最大収容人数
    recommended_capacity: int = Field(..., alias="recommendedCapacity")  # 推奨収容人数
    tags: list[str]  # タグ
    created_at: datetime  # 作成日時
    updated_at: datetime  # 更新日時
    labs_publication_date: datetime = Field(
        ..., alias="labsPublicationDate"
    )  # Labs公開日時
    publication_date: datetime = Field(..., alias="publicationDate")  # 公開日時
    thumbnail_image_url: Optional[str] = Field(
        None, alias="thumbnailImageUrl"
    )  # サムネイルURL
    release_status: ReleaseStatus = Field(..., alias="releaseStatus")  # リリース状態
    organization: str  # 組織
    version: int  # バージョン
    visits: int  # 訪問数
    popularity: int  # 人気度
    favorites: int  # お気に入り数
    heat: int  # 活発度


class InstanceInfo(BaseModel):
    id: str  # インスタンスID(wrld+instance)
    name: str  # インスタンス番号
    location: str  # ロケーション
    type: InstanceType  # インスタンスの種類
    group_instance_type: Optional[GroupInstanceType] = Field(
        None, alias="groupInstanceType"
    )  # グループインスタンスの種類
    instance_id: str = Field(..., alias="instanceId")  # インスタンスID(wrld+instance)
    short_name: str = Field(..., alias="secureName")  # 短縮名 (APIではsecureName,バグ?)
    user_count: int = Field(..., alias="userCount")  # 現在のユーザー数
    queue_enabled: bool = Field(..., alias="queueEnabled")  # キュー有効
    queue_size: int = Field(..., alias="queueSize")  # キューの人数
    region: str  # リージョン
    tags: list[str]  # タグ
    closed_at: Optional[datetime] = Field(None, alias="closedAt")
    world: WorldInfo  # ワールド情報
    world_id: str = Field(..., alias="worldId")  # ワールドID
    owner_id: Optional[str] = Field(
        None, alias="ownerId"
    )  # オーナーのID(Public -> None, Group -> groupId)


class GroupInstance(BaseModel):
    instance_id: str = Field(..., alias="instanceId")  # インスタンスID
    location: str  # ロケーション
    member_count: int = Field(
        ..., alias="memberCount"
    )  # グループメンバー数(userCountではない)
    world: WorldInfo  # ワールド情報


class WorldsInfo(WorldInfo):
    occupants: int  # 現在の総ユーザー数
    private_occupants: int = Field(
        ..., alias="privateOccupants"
    )  # プライベートインスタンスのユーザー数
    public_occupants: int = Field(
        ..., alias="publicOccupants"
    )  # パブリックインスタンスのユーザー数
    instances: list[InstanceEntry]  # インスタンス一覧

    @field_validator("instances", mode="before")
    @classmethod
    def parse_instances(cls, v):
        return [InstanceEntry.from_list(item) for item in v]


class GroupPostInfo(BaseModel):
    id: str = Field(..., alias="id")
    group_id: str = Field(..., alias="groupId")
    author_id: str = Field(..., alias="authorId")
    editor_id: Optional[str] = Field(None, alias="editorId")
    visibility: str = Field(..., alias="visibility")
    role_ids: list[str] = Field(default_factory=list, alias="roleIds")
    title: str = Field(..., alias="title")
    text: str = Field(..., alias="text")
    image_id: Optional[str] = Field(None, alias="imageId")
    image_url: Optional[str] = Field(None, alias="imageUrl")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")


class AuthVerifyResponse(BaseModel):
    verified: bool
