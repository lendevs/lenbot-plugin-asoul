"""Dynamics-site tools against a local copy of the public API shape."""

import json
from pathlib import Path

import pytest

from len_bot.next.plugin import Image, Text
from len_bot.next.plugin_testing import PluginTest

PACKAGE = Path(__file__).parents[1]


def config(source) -> dict:
    return {"calendar_url": source.url + "/calendar.ics", "dynamics_api_url": source.url + "/api", "remind_minutes": 0}


@pytest.mark.asyncio
async def test_member_list_and_latest_dynamics_query(source):
    source.json("/api/members", {"members": [{"id": "uid:672328094", "bilibiliUid": "672328094",
                                              "name": "嘉然", "avatarUrl": ""}]})
    source.json("/api/search", {"items": [], "total": 0, "nextCursor": None, "prevCursor": None})
    async with PluginTest(PACKAGE, config=config(source)) as bot:
        members = json.loads(await bot.tool("get_asoul_members", {}))
        assert members["data"]["members"][0]["id"] == "uid:672328094"
        latest = json.loads(await bot.tool("get_asoul_dynamics", {"member": "uid:672328094", "limit": 3}))
        assert latest["data"]["items"] == []
        assert source.requests[-1] == ("/api/search", {"member": ["uid:672328094"], "limit": ["3"], "sort": ["newest"]})


@pytest.mark.asyncio
async def test_dynamic_card_is_drawn_with_the_bundled_font(source):
    member = {"id": "uid:672328094", "bilibiliUid": "672328094", "name": "嘉然", "avatarUrl": ""}
    source.json("/api/search", {"items": [{
        "id": "1", "dynamicId": "1", "member": member, "type": "text", "contentText": "今晚七点见～",
        "publishedAt": "2026-10-06T12:00:00+08:00", "url": "https://t.bilibili.com/1", "images": [], "media": [],
        "likeCount": 3, "commentCount": 1, "forwardCount": 0}], "total": 1, "nextCursor": None, "prevCursor": None})
    async with PluginTest(PACKAGE, config=config(source)) as bot:
        result = json.loads(await bot.tool("send_asoul_dynamic_card", {"dynamic_id": "1"}))
        assert result["card_pages_prepared"] == 1
        card, link = bot.deliveries[-1].parts
        assert isinstance(card, Image) and "今晚七点见" in card.description
        assert isinstance(link, Text) and link.text == "https://t.bilibili.com/1"
