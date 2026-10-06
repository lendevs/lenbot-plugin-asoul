# 来源

本仓库由 `lenbot-personal` 中的 `asoul_calendar` 与 `asoul_dynamics` 两个插件合并而成（2026-10-05），解析与接口实现未改动。

## 日程（schedule.py、ics.py）

- 上游：[LEN5010/astrbot_plugin_asoul](https://github.com/LEN5010/astrbot_plugin_asoul) `5a945f695ecaa434ff71d402a344f8e9e40feab0`，许可证原件见 [LICENSE](LICENSE)（GNU AGPL v3）。
- `ics.py` 的 ICS 折行、转义与日期解析沿用 LenBot 旧插件 `src/len_bot/plugins/builtin/asoul_calendar/calendar.py`（同一上游移植）。
- 2026-09-28 按新插件接口 1 重写入口：旧卡片渲染器、成员别名表、插件内工作流不再保留；成员筛选改为按日历原文包含的文字匹配。
- 2026-10-06 日程卡片按 LenBot 面板配色和标志重新设计（`card_kit.py`、`schedule_card.py`），`card_kit.py` 与 `lenbot-plugin-bilibili` 各带一份。特别关注沿用上游 `/日程高亮` 命令用法，只保留一种高亮颜色。
- `assets/font.ttf` 是更纱黑体 Sarasa Mono SC Light，取自上游的 `font.ttf`，按 SIL Open Font License 1.1 分发；粗体用同色描边模拟。动态卡片也改用这份字体。
- `assets/stickers/` 是成员表情，取自上游的成员目录，缩到 160 像素并转为 WebP，版权归原权利人。

## 动态（dynamics.py、client.py、models.py、cards.py）

- A-SOUL 动态查询站：https://len5010.top/dynamics 。
- 2026-09-28 核对站点本机仓库 `dynamic_asoul`，提交 `9937469ca0b56f6b774735d2d9631e5c23e8ba53` 的 `docs/api.md`、`apps/api/src/app.ts`、`dynamic-mapper.ts`、`fanart-union.ts`、`packages/shared/src/types.ts` 和数据库查询的 `aroundId` 语义。
- 按当前公开 HTTP 协议独立实现，没有复制站点实现、旧插件渲染器、素材或账号状态。`aroundId` 返回邻近页，客户端必须比对实际目标 ID，不能取第一条作为详情。
- 旧插件使用的参考项目 `LEN5010/astrbot_plugin_dynamic_asoul` 的指定历史原文当前未取得，本实现不以它作为已核验协议或许可来源。
- 本插件代码采用 GNU AGPL v3 或更新版本，许可证原文见 LICENSE；查询和转发内容仍属于原作者。
