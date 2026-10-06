# 来源

本仓库由 `lenbot-personal` 中的 `asoul_calendar` 与 `asoul_dynamics` 两个插件合并而成（2026-10-05），解析与接口实现未改动。

## 日程（schedule.py、ics.py）

- 上游：[LEN5010/astrbot_plugin_asoul](https://github.com/LEN5010/astrbot_plugin_asoul) `5a945f695ecaa434ff71d402a344f8e9e40feab0`，许可证原件见 [LICENSE](LICENSE)（GNU AGPL v3）。
- `ics.py` 的 ICS 折行、转义与日期解析沿用 LenBot 旧插件 `src/len_bot/plugins/builtin/asoul_calendar/calendar.py`（同一上游移植）。
- 2026-09-28 按新插件接口 1 重写入口：旧卡片渲染器、成员别名表、插件内工作流不再保留；成员筛选改为按日历原文包含的文字匹配。
- 后续在接口1图文出口上接入显式字体的分页日程卡片，复用主仓库通用 TextCards；不复制旧字体和头像。

## 动态（dynamics.py、client.py、models.py、cards.py）

- A-SOUL 动态查询站：https://len5010.top/dynamics 。
- 2026-09-28 核对站点本机仓库 `dynamic_asoul`，提交 `9937469ca0b56f6b774735d2d9631e5c23e8ba53` 的 `docs/api.md`、`apps/api/src/app.ts`、`dynamic-mapper.ts`、`fanart-union.ts`、`packages/shared/src/types.ts` 和数据库查询的 `aroundId` 语义。
- 按当前公开 HTTP 协议独立实现，没有复制站点实现、旧插件渲染器、素材或账号状态。`aroundId` 返回邻近页，客户端必须比对实际目标 ID，不能取第一条作为详情。
- 旧插件使用的参考项目 `LEN5010/astrbot_plugin_dynamic_asoul` 的指定历史原文当前未取得，本实现不以它作为已核验协议或许可来源。
- 本插件代码采用 GNU AGPL v3 或更新版本，许可证原文见 LICENSE；查询和转发内容仍属于原作者。
