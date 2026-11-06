# 热辣榜 · hotboard

> 实时聚合全网热点榜单，一页看尽各大平台热门内容。

把「采集 → 落库 → 加工 → 展示」整条链路收进一个仓库：**一条 `docker compose up -d` 起全栈**。
端口、路径、密钥、采集方式全部走 `.env`，**不依赖任何宿主级反代** → 换机器（只搬一个数据目录）。

前后端分离 + 服务端渲染（SSR），首屏 HTML 自带完整列表，搜索引擎可直接抓取。

---

## 特性

- **68 个数据源**，覆盖综合 / 财经 / 科技 / 娱乐 / 开发 / 社区六大分类
- **SSR 首屏**：Astro + Vue，首屏 HTML 含完整内容，不依赖客户端 JS 渲染
- **历史与涨跌**：采集先落自有 PostgreSQL，前端只读自有库（绝不实时打源站）
- **关注 + 拖动排序**：关注的源置顶带星标；设置页可拖拽排序、控制显隐
- **深浅色主题**：纯 CSS 变量驱动，无 JS 注入样式，切换零闪变
- **局部刷新**：切源 / 切分类 / 点刷新都是 AJAX 局部更新，侧栏不重绘
- **无 CSS-in-JS**：样式随 CSS 文件到达即生效，首屏不会先裸样式再变正常
- **单机可跑**：4GB 内存足够

---

## 架构

```
            ┌──────────────── 采集（默认 30 分钟一轮）────────────────┐
            │  jobs/collector ──HTTP──> apps/engine  (源适配器引擎)     │
            └──────────────────────┬──────────────────────────────────┘
                                   ▼  只写自有库
                        db（PostgreSQL 16）  sources / items / snapshots
                                   │  只读
                                   ▼
                        apps/api（聚合接口 :6700）  排行 · 涨跌 · 热点推荐 · 分类
                                   │  /api 同源反代
                                   ▼
            apps/web-astro（SSR 前端 :6610）  Astro + Vue + 静态 CSS
```

**铁律：前端绝不实时打源站。** 采集先落**自有库**，前端只读自有库 —— history / 涨跌是护城河，也是和「实时转发源站」的根本区别。

---

## 快速开始

```bash
git clone <this-repo> hotboard && cd hotboard
cp .env.example .env        # 改 HOTBOARD_DATA_DIR / POSTGRES_PASSWORD
make init                   # 起服务 → 建表灌源 → 拉第一轮数据
make health                 # 容器 + HTTP 端点自检
```

`make init` 等价于 `make up-min && make bootstrap && make collect`。

首次启动会自动建表。等采集器跑完一轮（1~2 分钟）就能看到数据。

| 服务 | 地址 |
|---|---|
| 前端（SSR） | http://localhost:6610 |
| API | http://localhost:6700 |
| 健康检查 | http://localhost:6700/health |

### 采集触发方式

`COLLECT_CMD` 留空 → 采集容器空闲待命，由外部定时任务触发：

```bash
docker exec hotboard-collector python collect.py
```

或让它常驻自跑：

```bash
# .env
COLLECT_CMD=--loop --interval 1800
```

---

## 站点配置

所有和「具体部署」相关的个性化内容集中在**一个文件**：

```
apps/web-astro/src/config/site.ts
```

```ts
export const SITE = {
  name: "热辣榜",
  slogan: "汇聚全网热点，热门尽览无余",
  url: "https://example.com",   // 用于 canonical / sitemap / og
  brand: "#ff5722",
  icp:    { text: "", url: "" }, // 留空 → 不渲染备案块
  police: { text: "", url: "" },
  ad:     null,                  // null → 不渲染广告位
  links:  [],                    // 空数组 → 不渲染友链
  risingCount: 8,
  visibleSourceCount: 6,
};
```

**留空的项自动隐藏对应模块**，clone 下来不改也能跑。

---

## 目录结构

| 路径 | 作用 |
|---|---|
| `apps/web-astro` | **当前前端**：Astro SSR + Vue，静态 CSS |
| `apps/web` | 旧版 SPA 前端（Vue3 + Vite），保留作参考 |
| `apps/api` | 聚合接口（FastAPI，**只读**库：排行 / 涨跌 / 热点推荐 / 源清单） |
| `apps/engine` | 源适配器引擎（DailyHotApi 衍生） |
| `jobs/collector` | 采集器：每个源一个适配器文件 |
| `deploy/patches` | 对上游引擎的改动存档（升级上游时先 diff 再合并） |
| `docs` | 架构 · 部署 · 上游同步 |

数据**全部**落在 `${HOTBOARD_DATA_DIR}`：`pgdata/`、`collector-logs/`、`engine-logs/`、`backups/`。

---

## 新增数据源

在 `jobs/collector/adapters/` 下加一个文件，遵循统一接口：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""示例源"""
from .base import Item, clip, num, ts_ms

SRC_ID = "example"
NAME = "示例站"
CATEGORY = "综合"

def fetch(client) -> list[Item]:
    rows = (client.get_json("https://api.example.com/hot") or {}).get("data") or []
    out = []
    for i, x in enumerate(rows, 1):
        out.append(Item(
            ext_id=str(x["id"]),
            title=x["title"],
            url=x["url"],
            rank=i,
            heat=num(x.get("hot")),
            desc=clip(x.get("desc"), 300),
        ))
    return out
```

然后在 `jobs/collector/config.yml` 的 `bootstrap:` 里注册（首次建表时读一次，之后以库表 `sources` 为准）。

---

## 常用命令

`make help` 看全部。要点：

| 命令 | 说明 |
|---|---|
| `make up` / `down` / `ps` | 起 / 停（保留数据）/ 看状态 |
| `make health` | 容器 + HTTP 端点自检 |
| `make collect` | 立刻跑一轮采集 |
| `make logs S=web` | 跟踪指定服务日志 |
| `make psql` | 进数据库 |
| `make backup` | 备份库到 `$HOTBOARD_DATA_DIR/backups` |

---

## 关键约定（踩过坑的都在这里）

* **时区**：全链路 **+8（北京）** —— 容器（`TZ`）、数据库（`timezone`）、连接、代码一致。
* **分类**：**六个互斥分类**（综合 / 财经 / 科技 / 娱乐 / 开发 / 社区）。
  改分类只动 `jobs/collector/sql/seed_categories.sql`（幂等，`--bootstrap` 自动应用）
   —— 新库若没有分类种子，前端分类栏与「热点推荐」候选池会是空的。
* **源排序**：`jobs/collector/sql/seed_sort_order.sql`（幂等，`--bootstrap` 自动应用）。
   `sort_order` 为空时接口按 `order by sort_order nulls last, name` 排 → 按名称拼音瞎排，
   知乎会被挤到第 14 位、而前端标签默认只显示前 6 个 → 用户看不到头部源。
   新增源后往这个文件追加一行。
* **源清单**：以库表 `sources` 为准；`config.yml` 的 `bootstrap:` **只在首次建表时**读一次。
* **物化表 `current_items`**：切换源从 15s 降到 15ms 的关键。采集后会自动维护；
  如果前端切源很慢，先检查这张表有没有数据。
* **配置外部化**：`DB_HOST|PORT|NAME|USER`、`POSTGRES_PASSWORD`、
  `ENGINE_DAILYHOT_URL`、`ENGINE_NEWSNOW_URL` 等全部走 `.env`。
* **引擎可插拔**：`ENGINE_*_URL` 置空 = 停用该引擎（整批跳过，历史数据不动）。
* **不提交密钥**：`.env`、`*.env` 已进 `.gitignore`；只提交 `.env.example`。
* **前端 API 基址是相对路径 `/api`** → 由反代转到 api 容器：免 CORS、免写死 IP/域名，
  换域名 / 迁云**不用重新构建**前端。
* **改前端代码必须重新 build**：`apps/web-astro` 用 `build:` 把代码打进镜像，
  不是 volume 挂载（改完要 `docker compose build web-astro`）。

---

## 部署

见 [`docs/部署.md`](docs/部署.md)。

中国大陆部署**必须完成 ICP 备案**，备案号填到 `apps/web-astro/src/config/site.ts` 的 `icp` / `police` 字段。

---

## 免责声明

本项目仅聚合各平台**公开的热榜信息**并跳转到原站，不存储、不转载原文内容。
各站点内容版权归原平台所有。请合理设置采集频率，不要对源站造成压力。

---

## 许可证

[MIT](LICENSE)

本项目参考并移植了若干开源项目的实现，详见 [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)。
