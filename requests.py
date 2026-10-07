"""Business requests for the model tools; each action accepts only its own fields."""
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class Request(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')


class MembersQuery(Request):
    action: Literal['members']


class DynamicQuery(Request):
    action: Literal['search']
    query: Annotated[str, Field(description='全文关键词；空文本列最近动态')] = ''
    member: Annotated[str | None, Field(description='源站 member ID 或完整成员名；省略不限制', examples=['uid:672328094'])] = None
    dynamic_type: Annotated[Literal['text', 'image', 'video', 'forward', 'article', 'live', 'other'] | None, Field(description='按源站动态类型筛选；省略不限制')] = None
    start: Annotated[str | None, Field(description='ISO 起点，含时区')] = None
    end: Annotated[str | None, Field(description='ISO 终点，含时区')] = None
    sort: Annotated[Literal['newest', 'oldest', 'likes', 'comments'], Field(description='排序方式')] = 'newest'
    limit: Annotated[int, Field(description='最多条数', ge=1, le=100)] = 10
    cursor: Annotated[str | None, Field(description='上次 nextCursor，原样续页')] = None


class DynamicRead(Request):
    action: Literal['read']
    dynamic_id: Annotated[str, Field(description='来源 dynamicId，原样传递')]
    member: Annotated[str | None, Field(description='源站 member ID 或完整成员名；省略不限制', examples=['uid:672328094'])] = None


class HistoricalQuery(Request):
    action: Literal['history']
    month_day: Annotated[str | None, Field(description='同月同日 MM-DD；省略按本群时区的今天', examples=['10-06'])] = None
    sort: Annotated[Literal['hot', 'likes', 'comments'], Field(description='排序方式')] = 'hot'
    limit: Annotated[int, Field(description='最多条数', ge=1, le=100)] = 8


class FanartQuery(Request):
    action: Literal['search']
    query: Annotated[str, Field(description='关键词；空文本不筛选')] = ''
    character: Annotated[str | None, Field(description='角色名称，多角色用逗号分隔：贝拉、嘉然、乃琳、心宜&思诺')] = None
    content_type: Annotated[Literal['all', 'image', 'video', 'text', 'other'], Field(description='媒体类型；all 不筛选')] = 'all'
    kind: Annotated[Literal['all', 'fanart', 'material'], Field(description='二创或素材；all 不筛选')] = 'fanart'
    category: Annotated[str, Field(description='源站分类；all 不筛选')] = 'all'
    source: Annotated[Literal['all', 'bilibili', 'douban'], Field(description='来源平台；all 不筛选')] = 'all'
    sort: Annotated[Literal['newest', 'oldest', 'views', 'favorites'], Field(description='排序方式')] = 'newest'
    limit: Annotated[int, Field(description='最多条数', ge=1, le=100)] = 10
    cursor: Annotated[str | None, Field(description='上次 nextCursor，原样续页')] = None


class RandomFanart(Request):
    action: Literal['random']
    query: Annotated[str, Field(description='关键词；空文本不筛选')] = ''
    character: Annotated[str | None, Field(description='角色名称，多角色用逗号分隔：贝拉、嘉然、乃琳、心宜&思诺')] = None
    content_type: Annotated[Literal['all', 'image', 'video', 'text', 'other'], Field(description='媒体类型；all 不筛选')] = 'all'
    kind: Annotated[Literal['all', 'fanart', 'material'], Field(description='二创或素材；all 不筛选')] = 'fanart'
    source: Annotated[Literal['all', 'bilibili', 'douban'], Field(description='来源平台；all 不筛选')] = 'all'
    limit: Annotated[int, Field(description='最多条数', ge=1, le=100)] = 1


class DynamicCard(Request):
    action: Literal['dynamic']
    dynamic_id: Annotated[str, Field(description='来源 dynamicId，原样传递')]
    member: Annotated[str | None, Field(description='源站 member ID 或完整成员名；省略不限制', examples=['uid:672328094'])] = None
    include_images: Annotated[bool, Field(description='发送来源原图；false 只发正文与链接')] = True


class FanartCard(Request):
    action: Literal['fanart']
    source_dynamic_id: Annotated[str, Field(description='来源 sourceDynamicId；保留来源前缀')]
    include_images: Annotated[bool, Field(description='发送来源原图；false 只发正文与链接')] = True


DynamicsRequest = Annotated[MembersQuery | DynamicQuery | DynamicRead | HistoricalQuery, Field(discriminator='action')]
FanartRequest = Annotated[FanartQuery | RandomFanart, Field(discriminator='action')]
CardRequest = Annotated[DynamicCard | FanartCard, Field(discriminator='action')]
