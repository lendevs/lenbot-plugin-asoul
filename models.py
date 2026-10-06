"""Public dynamic_asoul DTOs; absent source values remain absent."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Count = Annotated[int, Field(ge=0)]
DynamicType = Literal['text', 'image', 'video', 'forward', 'article', 'live', 'other']


class DTO(BaseModel):
    model_config = ConfigDict(strict=True, extra='ignore')


class Member(DTO):
    id: str
    bilibiliUid: str
    name: str
    avatarUrl: str
    sign: str | None = None
    special: bool | None = None
    specialLabel: str | None = None


class Members(DTO):
    members: list[Member]


class Media(DTO):
    kind: Literal['image', 'video', 'cover', 'emoji', 'reserve', 'other']
    url: str | None = None
    ref: str | None = None
    title: str | None = None
    width: int | float | None = None
    height: int | float | None = None
    durationText: str | None = None
    label: str | None = None
    description: str | None = None
    badge: str | None = None
    actionText: str | None = None
    authorName: str | None = None


class Origin(DTO):
    dynamicId: str | None = None
    authorMid: str | None = None
    authorName: str
    publishedAt: int | float | None = None
    type: DynamicType | None = None
    text: str
    images: list[str]
    media: list[Media] | None = None
    url: str | None = None


class Dynamic(DTO):
    id: str
    dynamicId: str
    member: Member
    type: DynamicType
    contentText: str
    publishedAt: str
    url: str
    images: list[str]
    media: list[Media]
    orig: Origin | None = None
    rawHint: str | None = None
    likeCount: Count
    commentCount: Count
    forwardCount: Count
    eventKind: Literal['birthday'] | None = None
    eventSource: Literal['rule', 'manual'] | None = None

    @field_validator('publishedAt')
    @classmethod
    def timestamp(cls, value: str) -> str:
        if value and datetime.fromisoformat(value).utcoffset() is None:
            raise ValueError('publishedAt must be ISO time with timezone or empty')
        return value


class DynamicPage(DTO):
    items: list[Dynamic]
    total: Count
    nextCursor: str | None
    prevCursor: str | None


class HistoricalDay(DTO):
    monthDay: str
    sort: Literal['hot', 'likes', 'comments']
    items: list[Dynamic]


class Fanart(DTO):
    sourceDynamicId: str
    sourceDynamicUrl: str
    kind: Literal['fanart', 'material']
    contentType: Literal['image', 'video', 'text', 'other']
    mediaUrl: str | None
    category: str
    authorUid: str
    authorName: str
    authorAvatarUrl: str
    authorSpaceUrl: str
    characterTags: list[str]
    text: str
    images: list[str]
    viewCount: Count | None
    favoriteCount: Count | None
    statsFetchedAt: str | None


class Snapshot(DTO):
    id: str
    activatedAt: str
    moderationVersion: Count | None = None


class FanartPage(DTO):
    items: list[Fanart]
    total: Count
    nextCursor: str | None
    prevCursor: str | None
    snapshot: Snapshot
