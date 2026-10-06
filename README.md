# lenbot-plugin-asoul

LenBot 插件接口 1 的 A-SOUL 合集，插件名 `asoul`。包含两部分：

- **日程**：读取一个 ICS 日历（默认枝江站 `https://asoul.love/calendar.ics`），`/日程` 命令和「今日直播」全文直接回复安排，`live_schedule` 工具按日期查询，开播前向启用的群发场景事件。
- **动态**：访问 A-SOUL 动态查询站（默认 `https://len5010.top/dynamics/api`）的公开接口，查询成员、动态、历史同日和二创，并能把正文卡片和来源原图发到本群。不读取任何账号。

## 安装

在 LenBot 面板「能力 → 插件」填写本仓库的 Git 地址，或导入发布页的 ZIP，应用后配置参数并选择启用的群。也可以把仓库目录直接放进实例的 `plugins/`。

根配置的局部示例（不要覆盖完整根配置）：

```json
{
  "plugins": {
    "asoul": {
      "live_keywords": ["直播"],
      "card_mode": "image",
      "card_font": "/absolute/path/to/chinese-font.ttf"
    }
  },
  "scenes": {"onebot:group:10001": {"plugins": ["asoul"]}}
}
```

角色 `tools` 还需放行相应工具及 `tool_search`。

### 从旧的两个独立插件迁移

旧插件 `asoul_calendar` 与 `asoul_dynamics` 合并为 `asoul`，命令和工具名不变：

| 旧字段 | 新字段 |
|---|---|
| `asoul_calendar.source_url` | `calendar_url` |
| `asoul_calendar.cache_seconds` | `calendar_cache_seconds` |
| `asoul_calendar.user_agent` | `calendar_user_agent` |
| `asoul_dynamics.api_base_url` | `dynamics_api_url` |
| `asoul_dynamics.cache_seconds` | `dynamics_cache_seconds` |
| 两者的 `request_timeout_seconds`、`card_font` | 共用同名字段 |

其余日程字段（`calendar_timezone`、`live_keywords`、`non_live_keywords`、`include_all_day`、`remind_minutes`、`card_mode`）名称不变。场景 `plugins` 列表里的旧名字换成 `asoul`。旧数据目录里只有 `asoul_calendar/reminded.json` 需要移到新插件数据目录 `asoul/`，不移也只会在重启后对即将开始的条目重新提醒一次。

## 日程

- `/日程`、`/日程 明天`、`/日程 本周`，以及全文「今日直播」：插件直接回复，不叫醒大脑。`card_mode=text` 发文字，`image` 发分页卡片。
- 低频工具 `live_schedule(start, days, member)`：大脑经 `tool_search` 发现后按日期查询，`member` 按日历原文包含的文字筛选。
- 后台每分钟检查一次，开播前 `remind_minutes` 分钟向启用的群发一条场景事件，由大脑决定要不要提醒大家；已提醒的条目记在插件数据目录的 `reminded.json`，重启不重复提醒。`remind_minutes=0` 关闭提醒。

日历读取失败时命令如实回复没取到，不说成没有直播，原始错误进面板的插件错误。图片模式使用显式字体，完整保留长标题、日历描述和来源链接，不裁切，也不自动降级为文字；字体错误会导致插件加载失败。没有条目时如实回复未收录。

## 动态

- `get_asoul_members`：源站成员列表，后续筛选传 `uid:数字`。
- `get_asoul_dynamics`、`search_asoul_dynamics`：最近／关键词／类型／日期范围／分页。
- `read_asoul_dynamic`：按真实动态 ID 重新定位。特殊成员需传 `member`；不把相邻记录当目标。
- `get_asoul_on_this_day`：往年同月同日，默认本群时区的今天；源站此接口只查主库，不含今年和直播。
- `search_asoul_fanart`、`get_random_asoul_fanart`：二创、物料、B 站／豆瓣来源。随机查询不缓存。
- `send_asoul_dynamic_card`、`send_asoul_fanart_card`：发往调用场景，最多 32 页正文和 16 张来源原图。`include_images=false` 表示只发正文和链接。

发卡片会重新查询源项，正文、转发原文、指标和媒体信息分页排版，不裁剪长文。原图按来源顺序发送，保留 GIF，重复 URL 只发一次。全部内容准备好才开始发送；平台发送中途失败保留已确认的部分，不重发。返回的 `delivery` 是实际发送状态。

HTTP 单次请求，不跟随跳转、不读环境代理、不重试。成功的查询页最多缓存 16 页，过期后请求失败就报错，不返回旧页；源站返回的 409（快照已变化）原文返回。

## 字体

`card_font` 是日程图片和动态卡片共用的中文字体绝对路径，字体不随仓库提供，也不自动寻找或下载。留空时日程只能用文字模式，动态查询仍可用、发卡片会报配置错误。字体需要覆盖实际内容；卡片是结构化文字排版，不需要浏览器或模型。

## 开发

在与 LenBot 同级的目录里，用宿主的开发环境运行测试：

```sh
uv run --project ../LenBot --no-sync pytest -q
```

测试用本地 HTTP 服务模拟日历和动态站，不访问真实站点。真实源站和 QQ 内的展示效果未在测试中验证。

许可证：GNU AGPL v3 或更新版本，见 [LICENSE](LICENSE)；来源说明见 [SOURCE.md](SOURCE.md)。查询和转发的内容仍属于原作者。
