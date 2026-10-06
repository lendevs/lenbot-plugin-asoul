"""Calendar: live schedule from one ICS calendar, exact command, schedule tool and pre-live scene events."""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta
import json
from pathlib import Path
import time as clock
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

from len_bot.next.plugin import Image, Invocation, PluginContext, Text, background, command, fullmatch, tool
from len_bot.next.text_cards import CardSection, TextCards

from .ics import CalendarEvent, parse_calendar


WEEKDAYS = "一二三四五六日"
KEEP_REMINDED = 500


class CalendarFeature:
    def _init_calendar(self, ctx: PluginContext) -> None:
        url = urlsplit(ctx.config["calendar_url"])
        if url.scheme not in {"http", "https"} or not url.netloc:
            raise ValueError("calendar_url 必须是完整的 HTTP(S) 地址")
        self.calendar_zone = ZoneInfo(ctx.config["calendar_timezone"])
        if ctx.config["card_mode"] not in {"text", "image"}:
            raise ValueError("card_mode 必须明确为 text 或 image")
        if ctx.config["card_mode"] == "image" and not ctx.config["card_font"]:
            raise ValueError("image 模式必须配置 card_font 字体文件绝对路径")
        self.schedule_cards = TextCards(Path(ctx.config["card_font"])) if ctx.config["card_mode"] == "image" else None
        if ctx.config["request_timeout_seconds"] <= 0 or ctx.config["calendar_cache_seconds"] < 0 or ctx.config["remind_minutes"] < 0:
            raise ValueError("读取超时必须大于0，缓存秒数和提醒分钟数不能小于0")
        self.calendar_client = httpx.AsyncClient(timeout=ctx.config["request_timeout_seconds"], trust_env=False,
                                                 follow_redirects=False,
                                                 headers={"User-Agent": ctx.config["calendar_user_agent"]})
        self.calendar_snapshot: tuple[float, tuple[CalendarEvent, ...]] | None = None
        self.calendar_lock = asyncio.Lock()
        self.reminded_path = ctx.data_dir / "reminded.json"

    async def _stop_calendar(self) -> None:
        await self.calendar_client.aclose()

    async def events(self) -> tuple[CalendarEvent, ...]:
        async with self.calendar_lock:
            now = clock.time()
            if (self.calendar_snapshot is not None
                    and now < self.calendar_snapshot[0] + self.ctx.config["calendar_cache_seconds"]):
                return self.calendar_snapshot[1]
            response = await self.calendar_client.get(self.ctx.config["calendar_url"])
            if response.status_code != 200:
                raise RuntimeError(f"日历返回 HTTP {response.status_code}：{response.text[:300]!r}")
            events = parse_calendar(response.content.decode("utf-8-sig"), self.calendar_zone)
            self.calendar_snapshot = (now, events)
            return events

    def is_live(self, event: CalendarEvent) -> bool:
        config = self.ctx.config
        if event.cancelled or (event.all_day and not config["include_all_day"]):
            return False
        if event.url and "live.bilibili.com" in event.url:
            return True
        text = " ".join((event.title, event.categories, event.location)).casefold()
        if any(word.casefold() in text for word in config["live_keywords"]):
            return True
        return not any(word.casefold() in text for word in config["non_live_keywords"])

    async def between(self, start: datetime, end: datetime, member: str | None) -> list[CalendarEvent]:
        selected = []
        for event in await self.events():
            if not self.is_live(event):
                continue
            overlaps = (start <= event.start_at < end if event.end_at is None
                        else event.start_at < end and event.end_at > start)
            if overlaps and (member is None or member.casefold() in
                             " ".join((event.title, event.host_signature or "")).casefold()):
                selected.append(event)
        return selected

    def line(self, event: CalendarEvent, zone: ZoneInfo) -> str:
        start = event.start_at.astimezone(zone)
        when = f"{start:%m-%d} 周{WEEKDAYS[start.weekday()]} " + ("全天" if event.all_day else f"{start:%H:%M}")
        return f"{when} {event.title}" + (f"（{event.host_signature}）" if event.host_signature else "")

    @fullmatch("今日直播", "直接查看今日直播日程，不调用对话模型")
    async def today(self, ctx: Invocation) -> None:
        await self.schedule(ctx, "今天")

    @command("日程", "查看直播日程：/日程、/日程 明天、/日程 本周")
    async def schedule(self, ctx: Invocation, args: str) -> None:
        zone = ZoneInfo(ctx.timezone())
        today = datetime.fromtimestamp(ctx.now(), zone).date()
        spans = {"": (today, 1, "今天"), "今天": (today, 1, "今天"), "明天": (today + timedelta(days=1), 1, "明天"),
                 "本周": (today - timedelta(days=today.weekday()), 7, "本周")}
        if args not in spans:
            await ctx.reply("用法：/日程、/日程 明天、/日程 本周")
            return
        first, days, label = spans[args]
        start = datetime.combine(first, time.min, zone)
        try:
            events = await self.between(start, start + timedelta(days=days), None)
        except Exception as error:
            await ctx.reply(f"{label}日程暂时没取到，稍后再试。")
            raise
        if not events:
            await ctx.reply(f"{label}暂无直播。")
            return
        if self.schedule_cards is None:
            await ctx.reply(f"{label}直播安排（{zone.key}）：\n" + "\n".join(self.line(event, zone) for event in events))
            return
        sections = []
        for event in events:
            details = []
            if event.end_at is not None:
                details.append("结束：" + event.end_at.astimezone(zone).isoformat())
            if event.description:
                details.append(event.description)
            if event.location:
                details.append("地点：" + event.location)
            if event.url:
                details.append(event.url)
            sections.append(CardSection(self.line(event, zone), "\n".join(details)))
        pages = await asyncio.to_thread(self.schedule_cards.render, f"{label}直播安排",
                                        f"{first.isoformat()} 起 {days} 天 / {zone.key}",
                                        sections, source=self.ctx.config["calendar_url"])
        await ctx.reply_parts([*[Image(page.data, f"{label}日程 · 第 {index} 页\n{page.text}")
                                 for index, page in enumerate(pages, 1)], Text(self.ctx.config["calendar_url"])])

    @tool("live_schedule", "按日期查询直播日历；start 为 YYYY-MM-DD（本群时区），days 为天数，member 按日历原文包含的文字筛选")
    async def lookup(self, ctx: Invocation, start: str, days: int = 1, member: str | None = None) -> str:
        if not 1 <= days <= 31:
            raise ValueError("days 必须在 1 到 31 之间")
        zone = ZoneInfo(ctx.timezone())
        first = datetime.combine(date.fromisoformat(start), time.min, zone)
        events = await self.between(first, first + timedelta(days=days), member)
        return json.dumps({
            "source": self.ctx.config["calendar_url"], "timezone": zone.key,
            "range": [first.isoformat(), (first + timedelta(days=days)).isoformat()],
            "events": [{"uid": event.source_uid, "start": event.start_at.astimezone(zone).isoformat(),
                        "end": None if event.end_at is None else event.end_at.astimezone(zone).isoformat(),
                        "title": event.title, "host": event.host_signature, "url": event.url} for event in events],
            "note": "日历未收录不代表确定没有直播；日程时间不证明实际开播。",
        }, ensure_ascii=False)

    @background(every="1m")
    async def remind(self, ctx: PluginContext) -> None:
        minutes = ctx.config["remind_minutes"]
        if minutes == 0 or not ctx.scenes:
            return
        now = datetime.fromtimestamp(ctx.now(), self.calendar_zone)
        upcoming = await self.between(now, now + timedelta(minutes=minutes), None)
        reminded = json.loads(self.reminded_path.read_text(encoding="utf-8")) if self.reminded_path.exists() else []
        for event in upcoming:
            key = f"{event.source_uid}|{event.recurrence_id or ''}|{event.start_at.isoformat()}"
            if event.start_at <= now or key in reminded:
                continue
            for scene in ctx.scenes:
                zone = ZoneInfo(ctx.timezone(scene))
                left = max(1, round((event.start_at - now).total_seconds() / 60))
                await ctx.emit_event(scene, f"日历显示：{self.line(event, zone)}，大约还有 {left} 分钟开始。"
                                            "这是日历安排，不证明实际已经开播。")
            reminded = (reminded + [key])[-KEEP_REMINDED:]
            Path(self.reminded_path).write_text(json.dumps(reminded, ensure_ascii=False), encoding="utf-8")
