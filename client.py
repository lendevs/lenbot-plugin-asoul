"""One configured public site, bounded successful cache, no retries or stale results."""

import asyncio
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import BaseModel, ValidationError

from len_bot.next.image_assets import MAX_IMAGE_BYTES, inspect_image

from .models import Dynamic, DynamicPage, Fanart, FanartPage

MAX_RESPONSE_BYTES = 4_000_000
MAX_CACHED_PAGES = 16


def http_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError(f'需要不带账号口令的 HTTP(S) 地址：{value!r}')
    return value


@dataclass(frozen=True)
class Response[T: BaseModel]:
    data: T
    source: str
    fetched_at: str
    degraded: str | None

    def output(self) -> dict:
        return {'source': self.source, 'fetched_at': self.fetched_at,
                'degraded_sources': self.degraded,
                'data': self.data.model_dump(mode='json', exclude_unset=True),
                'note': '仅代表本站收录；未取得原平台实时详情或视频内容。'}


class Client:
    def __init__(self, base: str, *, timeout: float, ttl: float) -> None:
        self.base = http_url(base).rstrip('/') + '/'
        parsed = urlsplit(self.base)
        if parsed.query or parsed.fragment:
            raise ValueError('dynamics_api_url 不能含查询参数或片段')
        if timeout <= 0 or ttl < 0:
            raise ValueError('request_timeout_seconds 必须大于0，dynamics_cache_seconds 不能小于0')
        self.http = httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False,
                                      headers={'User-Agent': 'LenBot-ASoul-Dynamics/2.0'})
        self.ttl = ttl
        self.cache: OrderedDict[tuple, tuple[float, Response]] = OrderedDict()
        self.lock = asyncio.Lock()

    async def close(self) -> None:
        await self.http.aclose()

    async def query[T: BaseModel](self, endpoint: str, model: type[T], params: dict | None = None,
                                  *, cached: bool = True) -> Response[T]:
        params = {key: value for key, value in (params or {}).items() if value is not None}
        url = self.base + endpoint
        key = (endpoint, model, tuple(sorted(params.items())))
        async with self.lock:
            if cached and key in self.cache:
                expires, result = self.cache[key]
                if time.monotonic() < expires:
                    self.cache.move_to_end(key)
                    return result
                del self.cache[key]
            async with self.http.stream('GET', url, params=params) as response:
                body = await read_body(response, MAX_RESPONSE_BYTES)
                if response.status_code != 200:
                    raise RuntimeError(f'{response.url} HTTP {response.status_code}: {body[:600]!r}')
                try:
                    parsed = model.model_validate_json(body)
                except ValidationError as error:
                    raise ValueError(f'{response.url}: {error}; original={body[:600]!r}') from error
                result = Response(parsed, str(response.url), datetime.now(timezone.utc).isoformat(),
                                  response.headers.get('X-Data-Degraded'))
            if cached and self.ttl:
                self.cache[key] = (time.monotonic() + self.ttl, result)
                self.cache.move_to_end(key)
                while len(self.cache) > MAX_CACHED_PAGES:
                    self.cache.popitem(last=False)
            return result

    async def dynamic(self, dynamic_id: str, member: str | None) -> Response[Dynamic]:
        page = await self.query('search', DynamicPage, {'aroundId': dynamic_id, 'member': member, 'limit': 1}, cached=False)
        for item in page.data.items:
            if item.dynamicId == dynamic_id:
                return Response(item, page.source, page.fetched_at, page.degraded)
        raise LookupError(f'本站未返回动态 {dynamic_id!r}；特殊成员需要指定源 member ID。来源：{page.source}；'
                          f'实际返回ID：{[item.dynamicId for item in page.data.items]}；降级来源：{page.degraded}')

    async def fanart(self, source_id: str) -> Response[Fanart]:
        page = await self.query('fanart', FanartPage, {'aroundId': source_id, 'kind': 'all', 'limit': 1,
                                'source': 'douban' if source_id.startswith('douban:') else 'bilibili'}, cached=False)
        for item in page.data.items:
            if item.sourceDynamicId == source_id:
                return Response(item, page.source, page.fetched_at, page.degraded)
        raise LookupError(f'本站未返回二创 {source_id!r}。来源：{page.source}；'
                          f'实际返回ID：{[item.sourceDynamicId for item in page.data.items]}；降级来源：{page.degraded}')

    async def image(self, source: str) -> bytes:
        # Root-relative site media paths follow URL semantics; no guessed local files.
        url = http_url(urljoin(self.base, source))
        async with self.http.stream('GET', url) as response:
            data = await read_body(response, MAX_IMAGE_BYTES)
            if response.status_code != 200:
                raise RuntimeError(f'图片 {response.url} HTTP {response.status_code}: {data[:300]!r}')
        inspect_image(data)
        return data


async def read_body(response: httpx.Response, limit: int) -> bytes:
    data = bytearray()
    async for chunk in response.aiter_bytes():
        if len(data) + len(chunk) > limit:
            raise ValueError(f'{response.url}: 响应超过 {limit} 字节；original={bytes(data[:100])!r}')
        data.extend(chunk)
    return bytes(data)
