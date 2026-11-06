# 评估：热度聚合源统一替换为 RSSHub？

> 评估时间：2026-10-16 ｜ 方法：**实测**（自建 RSSHub 容器 + 逐个 route 探针 + 与你现有库数据对照），不是凭印象。
> 结论：**不建议统一替换**；建议作为**新增的第二类采集器（engine=rsshub）**并存。

## 一、现状（实测自库）

| 项 | 事实 |
|---|---|
| 采集引擎 | `dailyhot` **50 源** + `newsnow` **33 源** = **83 源** |
| 类别分布 | 综合 30 / 开发 16 / 娱乐 13 / 科技 13 / 社区 8 / 购物 3 |
| items 关键字段 | `ext_id, title, url, url_hash, meta{hot, desc, cover, author, timestamp}` |
| **snapshots 关键字段** | **`rank`（榜单名次）+ `heat`（热度数值）+ ts** ⭐ |
| 数据样例 | `dailyhot:36kr` → rank 1..N，heat 39/82/12/7/20 —— **有排名也有热度** |

→ **`rank + heat` 的时序 = 涨跌/趋势 = 本项目的护城河**。任何换源方案必须先回答：**还能不能给出这两个字段**。

## 二、RSSHub 实测结果（自建容器，v 最新）

### 2.1 能跑通的（并给出字段解析）

| Route | 结果 | item 字段 | 有 rank/heat？ |
|---|---|---|---|
| `/zhihu/hot` 知乎热榜 | ✅ 200，30 条 | title / description / link / guid / pubDate / dc:creator | ❌ **无**（description 仅 11 字符「[图片]」）|
| `/36kr/hot-list` 36氪热榜 | ✅ 200，8 条 | title / description / link / guid / pubDate | ❌ **无**（description 是**整篇正文**，1 万+ 字符）|
| `/36kr/newsflashes` 快讯 | ✅ 200，20 条 | 同上 | ❌ 无 |
| `/juejin/category/frontend` 掘金 | ✅ 200，20 条 | + category | ❌ 无 |

### 2.2 需要额外配置 / 不可用的

| Route | 结果 | 原因（容器日志原文） |
|---|---|---|
| `/weibo/search/hot` 微博热搜 | ❌ **503** | `Cooling down before new visitor Cookies may be fetched` —— 需 visitor cookie，且有冷却 |
| `/github/trending/daily/*` | ❌ **503** | `GitHub trending RSS is disabled due to the lack of relevant config` —— 需配 token |
| `/bilibili/ranking/...` | ⚠️ 301 | route 已迁移 |
| 抖音热榜 | ❌ 无对应 route | 命名空间只有 `/hashtag`、`/user` |
| 今日头条热榜 | ❌ 无对应 route | 命名空间只有 `/channel/:category` |

### 2.3 权威 route 名怎么拿（避免猜）
```bash
docker run -d --rm -p 1200:1200 docker.1ms.run/diygod/rsshub
curl -s http://127.0.0.1:1200/api/namespace/zhihu   # 返回该命名空间全部 route
```

## 三、结论

**RSSHub 的语义是「内容订阅（文章流）」，不是「榜单（rank + heat）」** —— 这是根本性不匹配。

因此：

1. **统一替换 = 把「热榜产品」退化成「RSS 阅读器」** ⚠️
   - `rank` 消失 → 涨跌/趋势/榜单对比全部失效（护城河没了）
   - `heat` 消失 → 热度数值与排序权重无从计算
2. **覆盖面不增反减** ⚠️：微博 / GitHub trending 需额外 cookie·token；抖音热榜、头条热榜**没有 route**
3. **运维成本上升** ⚠️：自建要维护 cookie / token / 代理，route 被源站改版打断的频率不低（社区修复有延迟）

### 建议的正确用法（不替换，做加法）

| 用途 | 用什么 | 理由 |
|---|---|---|
| **榜单类源（要 rank + heat）** | **保持 dailyhot + newsnow** ✅ | 直接给结构化 `hot`，语义就是榜单 |
| **长尾内容站 / 你没覆盖的站点** | **新增 `engine=rsshub`** ✅ | 复用社区几千条 route，维护成本外移 |
| **需要全文内容的场景** | RSSHub ✅ | 它的 description 常是**整篇正文**（本库现在只有摘要）|

### 若采纳（落地要点）
- `sources` 表已是 `engine + src_id` 结构，**新增引擎不用改表** → 采集器加一个 rsshub 适配器即可
- 常驻化要求（按本项目规范）：`docker compose` + 外部数据卷 + `restart: unless-stopped` + 登记 Dashy
- 必须配 `RSSHUB_*` 相关配置（微博 cookie、GitHub token、代理）才能覆盖热门源
- **不要动 snapshots 的写入路径**：任何新源若拿不到 heat，只能进 items，不许污染 snapshots 的 heat 语义

## 四、待办（若决定推进）

- [ ] 决定：是「只加长尾源」还是「连榜单源也做双写对比」
- [ ] 逐条比对 83 个源 → RSSHub route 映射表（可直接换成 rsshub 的数量）
- [ ] 自建 RSSHub 常驻容器 + 配置 cookie/token + Dashy 登记
- [ ] 采集器新增 `engine=rsshub` 适配器（RSS/Atom 解析 → items；**不写 snapshots.heat**）

---

## 五、⏹️ 2026-10-19 更新：本文的「接入 RSSHub 作为 engine」方案**已作废**，理由有二

1. **许可**：RSSHub 是 **AGPL-3.0**（实测 `/app/package.json`），**不是 MIT**。
   本项目 P2 已把 63 个源全部自研化，再引入一个 AGPL 上游做公开运营的后端，
   有网络服务条款下的开源义务风险 → **不采用**。
2. **架构已变**：dailyhot / newsnow 两个外部引擎已下线（源全部自研适配器），
   `custom` 是唯一引擎；此时再加一个 `engine=rsshub` 等于把刚摘掉的外部依赖装回去。

**现行结论**：RSSHub **只当"源目录"用** —— 用它确认"某源存在且在更新"，然后**自己实测端点写适配器**
（能拿到真热度，且不受 AGPL 约束）。详见 `docs/RSSHub源发现清单.md`
（含 4415 路由实测、52 个中文命名空间清单、A/B 档候选源、复现方法）。
