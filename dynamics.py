"""Dynamics: dedicated public-site queries and explicit card delivery through the scene outlet."""

import asyncio
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from len_bot.next.plugin import Image, Invocation, PluginContext, Text, tool
from len_bot.next.text_cards import CardSection, TextCards

from .cards import dynamic_sections, fanart_sections
from .client import Client, Response
from .models import Dynamic, DynamicPage, Fanart, FanartPage, HistoricalDay, Members


class DynamicsFeature:
    def _init_dynamics(self, ctx: PluginContext) -> None:
        self.dynamics_cards = TextCards(Path(ctx.config['card_font'])) if ctx.config['card_font'] else None
        self.dynamics_client = Client(ctx.config['dynamics_api_url'], timeout=ctx.config['request_timeout_seconds'],
                                      ttl=ctx.config['dynamics_cache_seconds'])

    async def _stop_dynamics(self) -> None:
        await self.dynamics_client.close()

    @tool('get_asoul_members', '读取动态站成员列表，使用返回的真实 member id（uid:数字）筛选，不猜成员别名')
    async def members(self, ctx: Invocation) -> str:
        return encode((await self.dynamics_client.query('members', Members)).output())

    @tool('get_asoul_dynamics', '查询本站收录的最近动态；member 为 get_asoul_members 返回的 ID。不是原平台实时全量动态')
    async def latest(self, ctx: Invocation, member: str | None = None, limit: int = 10, cursor: str | None = None) -> str:
        return encode((await self.dynamics_client.query('search', DynamicPage,
                       {'member': member, 'limit': limit, 'cursor': cursor, 'sort': 'newest'})).output())

    @tool('search_asoul_dynamics', '搜索动态站全文/用户名；时间用带时区ISO文本，翻页原样传 nextCursor，member 用来源 uid:数字')
    async def search(self, ctx: Invocation, query: str, member: str | None = None,
                     dynamic_type: Literal['text', 'image', 'video', 'forward', 'article', 'live', 'other'] | None = None,
                     start: str | None = None, end: str | None = None,
                     sort: Literal['newest', 'oldest', 'likes', 'comments'] = 'newest',
                     limit: int = 10, cursor: str | None = None) -> str:
        return encode((await self.dynamics_client.query('search', DynamicPage,
                       {'q': query, 'member': member, 'type': dynamic_type, 'from': start, 'to': end,
                        'sort': sort, 'limit': limit, 'cursor': cursor})).output())

    @tool('read_asoul_dynamic', '按真实 dynamicId 定位本站动态正文；特殊成员需带 member ID；不会把相邻记录当作目标')
    async def read(self, ctx: Invocation, dynamic_id: str, member: str | None = None) -> str:
        return encode((await self.dynamics_client.dynamic(dynamic_id, member)).output())

    @tool('get_asoul_on_this_day', '查询往年同月同日动态（源站只查主库，不含今年/直播）；month_day 为 MM-DD，省略按本群今天')
    async def history(self, ctx: Invocation, month_day: str | None = None,
                      sort: Literal['hot', 'likes', 'comments'] = 'hot', limit: int = 8) -> str:
        day = month_day if month_day is not None else datetime.fromtimestamp(ctx.now(), ZoneInfo(ctx.timezone())).strftime('%m-%d')
        return encode((await self.dynamics_client.query('on-this-day', HistoricalDay,
                       {'monthDay': day, 'sort': sort, 'limit': limit})).output())

    @tool('search_asoul_fanart', '查询二创/物料；character 多角色逗号分隔（贝拉、嘉然、乃琳、心宜&思诺），分页用来源游标')
    async def fanart(self, ctx: Invocation, query: str = '', character: str | None = None,
                     content_type: Literal['all', 'image', 'video', 'text', 'other'] = 'all',
                     kind: Literal['all', 'fanart', 'material'] = 'fanart', category: str = 'all',
                     source: Literal['all', 'bilibili', 'douban'] = 'all',
                     sort: Literal['newest', 'oldest', 'views', 'favorites'] = 'newest',
                     limit: int = 10, cursor: str | None = None) -> str:
        return encode((await self.dynamics_client.query('fanart', FanartPage,
                       {'q': query, 'character': character, 'contentType': content_type, 'kind': kind,
                        'category': category, 'source': source, 'sort': sort, 'limit': limit, 'cursor': cursor})).output())

    @tool('get_random_asoul_fanart', '随机查询二创，不使用缓存；图片只返回来源URL，不代表已经看到或发出图片')
    async def random_fanart(self, ctx: Invocation, query: str = '', character: str | None = None,
                            content_type: Literal['all', 'image', 'video', 'text', 'other'] = 'all',
                            kind: Literal['all', 'fanart', 'material'] = 'fanart',
                            source: Literal['all', 'bilibili', 'douban'] = 'all', limit: int = 1) -> str:
        return encode((await self.dynamics_client.query('fanart', FanartPage,
                       {'q': query, 'character': character, 'contentType': content_type, 'kind': kind,
                        'source': source, 'limit': limit, 'random': '1'}, cached=False)).output())

    @tool('send_asoul_dynamic_card', '重新读取真实dynamicId，渲染完整正文卡片并发到本群；可附来源原图，不播放视频。需配置card_font；回报实际发送状态')
    async def send_dynamic(self, ctx: Invocation, dynamic_id: str, member: str | None = None,
                           include_images: bool = True) -> str:
        self.require_cards()
        response = await self.dynamics_client.dynamic(dynamic_id, member)
        return await self.send(ctx, response, dynamic_sections(response.data), response.data.url, include_images)

    @tool('send_asoul_fanart_card', '读取真实sourceDynamicId（含douban:ID），渲染卡片并发到本群；可附来源原图。需配置card_font；回报实际发送状态')
    async def send_fanart(self, ctx: Invocation, source_dynamic_id: str, include_images: bool = True) -> str:
        self.require_cards()
        response = await self.dynamics_client.fanart(source_dynamic_id)
        return await self.send(ctx, response, fanart_sections(response.data), response.data.sourceDynamicUrl, include_images)

    def require_cards(self) -> TextCards:
        if self.dynamics_cards is None:
            raise ValueError('发卡片需要在根配置 plugins.asoul.card_font 填写字体文件绝对路径')
        return self.dynamics_cards

    async def send(self, ctx: Invocation, response: Response[Dynamic] | Response[Fanart],
                   document: tuple[str, str, list[CardSection], list[str]], source: str, include_images: bool) -> str:
        renderer = self.require_cards()
        title, subtitle, sections, urls = document
        if include_images and len(urls) > 16:
            raise ValueError(f'来源有 {len(urls)} 张图片，超过单次16张；可明确 include_images=false 只发正文卡片')
        if response.degraded is not None:
            sections.insert(0, CardSection('来源报告数据降级', response.degraded))
        if urls and not include_images:
            sections.append(CardSection('来源图片链接（本次不发原图）', '\n'.join(urls)))
        pages = await asyncio.to_thread(renderer.render, title, subtitle, sections, source=source)
        parts = [Image(page.data, f'{title} · 第 {index} 页\n{page.text}') for index, page in enumerate(pages, 1)]
        if include_images:
            for index, url in enumerate(urls, 1):
                parts.append(Image(await self.dynamics_client.image(url), f'{title} · 来源原图 {index}: {url}；未做视觉分析'))
        parts.append(Text(source))
        sent = await ctx.reply_parts(parts)
        return encode({'delivery': asdict(sent), 'card_pages_prepared': len(pages),
                       'source_images_prepared': len(urls) if include_images else 0,
                       'source_images_omitted': [] if include_images else urls,
                       'source': response.source, 'fetched_at': response.fetched_at,
                       'degraded_sources': response.degraded})


def encode(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False)
