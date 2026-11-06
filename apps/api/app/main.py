"""hotboard-api —— 热榜聚合站自己的只读接口（读 hotdb）

设计要点
- 前端绝不直连源站；本服务**只读我们自己的 Postgres**（hotdb）。
- 响应形状兼容 `imsyy/DailyHot`（`{code,name,title,data:[...]}`），前端模板零改动即可渲染。
- **源清单按源名合并**（同名源只出现一次，避免"两个知乎"）；但**条目层默认不合并**：
  同一源在多个引擎里都有时，**默认只显示「主引擎」那一版，并按源站名次（snapshots.rank）排序**，
  忠实还原源站榜单。
  ⚠️ 各引擎的**截断长度不同**（实测知乎：dailyhot 30 条 / newsnow 20 条，交集 19、前 5 条顺序一致）
  → 主引擎取**条目更多**的那个（更完整），另一引擎的价值是**冗余备份**（主引擎挂/被墙时顶上）。
  需要并集时显式加 `?merge=1`（主引擎在前，其他引擎的独有条目追加在后，不按热度混排）。
  要看单个引擎用 `/{engine}:{name}`（例 `/newsnow:zhihu`）。

端点
  GET /                        服务索引
  GET /health                  健康检查
  GET /sources                 合并后的源清单（唯一源名 + 分类 + 各引擎 + 是否有图标）
  GET /all                     DailyHot 兼容的 routes 形状（唯一源名）
  GET /{源名}?limit=50          主引擎那一版，按源站名次排序
  GET /{源名}?merge=1           并集：主引擎在前 + 其他引擎独有条目追加
  GET /{引擎:源名}              单引擎视图
"""
import json
import os
import re
from datetime import datetime, timedelta, timezone

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg.rows import dict_row

HERE = os.path.dirname(os.path.abspath(__file__))
# ⭐ 时区统一 +8（北京）：所有对外时间都按北京时区呈现（见手册《时区规范》）
BJ = timezone(timedelta(hours=8))
with open(os.path.join(HERE, "labels.json"), encoding="utf-8") as fh:
    LABELS = json.load(fh)
with open(os.path.join(HERE, "logos.json"), encoding="utf-8") as fh:
    LOGO_KEYS = set(json.load(fh))  # 前端 public/logo/<key>.png 实际存在的图标

DB = {
    "host": os.getenv("DB_HOST", "hotdb"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("POSTGRES_DB", "hotboard"),
    "user": os.getenv("POSTGRES_USER", "hotboard"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
}
# 分类显示顺序（2026-10-12 第三版：收敛为六个两字分类，用户指定）
CATEGORY_ORDER = ["综合", "财经", "科技", "娱乐", "开发", "社区", "其他"]

# 📈 热点推荐的候选池：**只从这些分类里挑**（用户指定：从「综合」「科技」出）
#    （不要从全部分类找 —— 否则会刷到"游戏版本更新/装备补给"这类不是新闻的条目）
RISING_CATS = ["综合", "科技"]

# ⭐ 源的默认展示顺序（2026-10-12 人工编排：按**知名度 + 内容质量**，参考 rebang.today 的 tab 顺序）
#   未列入清单的源自动排到后面（按名称兜底）。
#   优先级：用户在「设置」里的自定义排序 > 这里的默认顺序。
#   编排原则：① 同类里"更常看/更权威"的靠前 ② 门户/聚合类靠前、垂类靠后
#             ③ 无热度/无时间且质量一般的靠后；④ RSS 类源尽量不压在头条位置
SOURCE_ORDER = [
    # 综合（热搜榜 + 新闻资讯，日常打开率最高）
    "zhihu", "weibo", "baidu", "douyin", "toutiao", "kuaishou", "tieba", "zhihu-daily",
    "qq-news", "thepaper", "sina-news", "netease-news", "nytimes", "sina",
    # 科技（科技数码）
    "36kr", "ithome", "huxiu", "sspai", "ifanr", "geekpark", "guokr", "dgtle",
    # 娱乐（游戏动漫 + 影音娱乐）
    "lol", "genshin", "starrail", "miyoushe", "honkai", "yystv", "ithome-xijiayi",
    "bilibili", "douban-movie", "acfun", "weread",
    # 开发（编程开发）
    "github", "juejin", "v2ex", "csdn", "52pojie", "hellogithub", "nodeseek", "jianshu",
    "51cto", "hackernews",
    # 社区（社区论坛 + 生活）
    "hupu", "ngabbs", "douban-group", "newsmth", "weatheralarm", "history",
    # 购物
    "smzdm",
]
SRC_RANK = {name: i for i, name in enumerate(SOURCE_ORDER)}

# 只展示哪些引擎的源（逗号分隔）。
# 2026-10-10 用户决定：**先以 dailyhot 的源为主，暂停 newsnow**
# （newsnow 知乎等源上限只给 20 条、源粒度也不一致；库里历史数据保留）。
# 恢复 newsnow：把下面默认值改成 "dailyhot,newsnow"（或改 hotapi/.env）。
ENGINES = [e.strip() for e in os.getenv("ENGINE_WHITELIST", "dailyhot").split(",") if e.strip()]

# 每个分类下的「聚合项」（对标 rebang：切到某分类时默认选中的那个汇总源）
AGG_LABELS = {
    "综合": "全站", "科技": "热榜科技", "开发": "热榜开发", "游戏娱乐": "热榜娱乐",
    "社区": "热榜社区", "购物": "热榜购物", "财经": "热榜财经", "其他": "热榜其他",
}


def agg_key(cat: str) -> str:
    return f"agg:{cat}"

# ⭐ 忠实性关键：**当前榜单 = 该源最新一次采集的那一批**
# （items 表是历史累计，直接查会把"历史上出现过、现在已掉榜"的条目也带出来，
#   实测会出现 50 条 + 名次重复 [1,2,3,4,5,6,6,7,8,8]）
LATEST_TS = """(select max(sn.ts) from snapshots sn
                 join items i2 on i2.id = sn.item_id
                where i2.source_id = {sid})"""

# meta.hot 作为兜底（可能缺失或为字符串）
HOT_EXPR = "coalesce(nullif(regexp_replace(coalesce(i.meta->>'hot',''),'[^0-9.]','','g'),'')::numeric, 0)"

app = FastAPI(title="hotboard-api", version="0.4.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


def conn():
    # 连接级会话时区也钉成 +8：这样库里 timestamptz 读出来就带 +08:00
    return psycopg.connect(**DB, row_factory=dict_row, connect_timeout=8,
                           options="-c timezone=Asia/Shanghai")


def _shrink_zhimg(u: str) -> str:
    """知乎图床缩小到缩略图。

    实测原图 86–610KB/张，一页 27 张 ≈ 1.3MB+，连续切几次数据源就把连接池塞满，
    表现是「列表换了但图一直不出来」，体感好几秒。加 `_l` 后缀后单张 3–20KB。

    知乎 URL 有几种形态，都要能处理（实测全部返回 200 且变小）：
      https://pic1.zhimg.com/v2-<hash>.png                      → _l.jpg  282KB→18KB
      https://pic4.zhimg.com/v2-<hash>_1440w_l.jpg              → _l.jpg  610KB→20KB
      https://pica.zhimg.com/50/v2-<hash>_b.jpg                 → _l.jpg   86KB→8.6KB
      https://pic1.zhimg.com/80/v2-<hash>_1440w.webp?source=... → _l.jpg   97KB→3.3KB

    做法：只保留主机 + `v2-<hash>`，丢掉路径里的尺寸段、任何后缀和 query。
    注意：`_b` 仍是 256KB、`_720w` 不生效，只有 `_l/_m/_s/_xs` 是真小图。
    """
    m = re.match(
        r"^https?://(pic[0-9a-z]*\.zhimg\.com)/(?:[^/]+/)?(v2-[0-9a-z]+)[^/?#]*",
        u, re.I)
    if m:
        return f"https://{m.group(1)}/{m.group(2)}_l.jpg"
    return u


def clean_cover(u: str) -> str:
    """封面 URL 清洗：有的 RSS 源会把绝对地址再套一层站点前缀
    （实测 52pojie 返回 `https://www.52pojie.cn/https://attach.52pojie.cn/...`）→ 取内层地址，
    否则浏览器加载必然 404（前端虽有 @error 兜底，但那等于白拿了一张图）。
    顺带把知乎图床换成缩略图尺寸（体积省 94%）。"""
    u = (u or "").strip()
    m = re.match(r"^https?://[^/]+/(https?://.+)$", u)
    if m:
        u = m.group(1)
    return _shrink_zhimg(u)


def label_of(name: str) -> str:
    return LABELS.get(name) or name


# ⭐ 简介长度统一截断（2026-10-12）：各源简介长度差异极大
# （实测爱范儿平均 2724 字、纽约时报 549 字，而微博只有 12 字），不截断会"一屏全是字"。
# 在标点/空格处收尾再补省略号，避免把词切一半。
DESC_MAX = int(os.getenv("DESC_MAX", "120"))


# 论坛类源的简介常带 BBCode（实测吾爱破解：`[hr][md] **标题** …`）→ 只清常见标签，别误伤正文的方括号
BBCODE = re.compile(
    r"\[/?(?:hr|md|b|i|u|s|url|img|quote|code|attach|size|color|font|align|list|\*|table|tr|td|flash|media|hide|free|sell|indent|float|center|p)(?:=[^\]]*)?\]",
    re.I,
)


def short_desc(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s or "")          # 有的源简介带 HTML（实测爱范儿返回 <p>…）
    s = BBCODE.sub(" ", s)                        # 论坛 BBCode（吾爱破解等）
    s = s.replace("**", "")                       # Markdown 粗体标记
    s = re.sub(r"&nbsp;?", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) <= DESC_MAX:
        return s
    cut = s[:DESC_MAX]
    m = max(cut.rfind(ch) for ch in "。！？；，、.!?;, ")
    if m >= int(DESC_MAX * 0.6):
        cut = cut[:m]
    return cut.rstrip("。！？；，、.!?;, ") + "…"


def logo_key(name: str):
    """有图标文件才返回 key；否则 null（前端用文字头像，避免碎图）"""
    return name if name in LOGO_KEYS else None


@app.get("/")
def index():
    return {
        "service": "hotboard-api",
        "note": "热榜站自己的只读接口，读 hotdb；前端（:6600）只打这里",
        "endpoints": {
            "/health": "健康检查",
            "/sources": "合并后的源清单（唯一源名，含分类/各引擎/图标）",
            "/all": "DailyHot 兼容 routes 形状",
            "/{源名}?limit=50": "主引擎那一版，按源站名次排序（默认）",
            "/{源名}?merge=1": "并集：主引擎在前 + 其他引擎独有条目追加",
            "/{引擎:源名}": "单引擎视图，例 /newsnow:zhihu",
        },
    }


@app.get("/health")
def health():
    with conn() as c, c.cursor() as cur:
        cur.execute("select count(distinct name) as names, count(*) as rows from sources")
        r = cur.fetchone()
    return {"ok": True, "unique_sources": r["names"], "source_rows": r["rows"],
            "engines": ENGINES}


@app.get("/sources")
def sources():
    """按源名合并的唯一源清单；只统计**启用引擎**（ENGINE_WHITELIST）的源。

    ⭐ 2026-10-21 性能修复：latest_items 原先是对每行 sources 执行的**相关子查询**
    （每行都要在 140 万行 snapshots 上算一次 max(ts) 再 count），68 个源 = 68 次重扫。
    ⭐ 2026-10-22 Step 1：直接数 current_items（物化表只有几千行）→ 毫秒级。
    """
    sql = """
        select s.name, s.id as sid, s.engine, s.category, s.enabled, s.last_ok_at, s.sort_order,
               coalesce(c.cnt, 0) as latest_items,
               (select count(*) from items i where i.source_id = s.id) as total_items
        from sources s
        left join (select source_id, count(*) as cnt from current_items group by source_id) c
               on c.source_id = s.id
        where s.engine = any(%s) and s.enabled
        order by s.sort_order nulls last, s.name
    """
    with conn() as c, c.cursor() as cur:
        cur.execute(sql, (ENGINES,))
        rows = cur.fetchall()

    grouped: dict[str, dict] = {}
    for r in rows:
        g = grouped.setdefault(r["name"], {
            "name": r["name"],
            "key": logo_key(r["name"]),
            "label": label_of(r["name"]),
            "category": r["category"] or "其他",
            "engines": [],
            "items": 0,          # 当前榜单条数（最新一批）
            "totalItems": 0,     # 历史累计
            "lastOkAt": None,
            "display": False,
        })
        g["engines"].append({"engine": r["engine"], "items": r["latest_items"],
                             "totalItems": r["total_items"], "enabled": bool(r["enabled"])})
        g["items"] = max(g["items"], r["latest_items"])
        g["totalItems"] += r["total_items"]
        # ⭐ 默认顺序以**库里的 sort_order** 为准（用户随时可在库里调整）
        if g.get("ord") is None or (r["sort_order"] is not None and r["sort_order"] < g["ord"]):
            g["ord"] = r["sort_order"]
        if r["enabled"] and (r["latest_items"] > 0 or r["total_items"] > 0):
            g["display"] = True
        if r["last_ok_at"] and (g["lastOkAt"] is None or r["last_ok_at"].isoformat() > g["lastOkAt"]):
            g["lastOkAt"] = r["last_ok_at"].isoformat()
        # 第一条即最新一批条数最多者（SQL 已按 latest_items 降序）→ 主引擎
        if "primary" not in g:
            g["primary"] = r["engine"]
            g["primaryItems"] = r["latest_items"]

    # 排序：① 以**库里的 sort_order** 为准（默认顺序的唯一来源，用户可自行调整）
    #      ② 未设 sort_order 的按名称兜底
    #      （旧版 SOURCE_ORDER/SRC_RANK 是死代码：它用 src_id 查表，却拿中文显示名去比对，永远命中不了）
    out = sorted(grouped.values(),
                 key=lambda x: (x["ord"] if x.get("ord") is not None else 10 ** 6, x["name"]))
    shown = [s for s in out if s["display"]]
    cats = [c for c in CATEGORY_ORDER if any(s["category"] == c for s in shown)]

    # 每个分类的聚合项（前端置顶 + 默认选中；对标 rebang 的「全站 / 热榜科技 …」）
    aggregates = []
    for c in cats:
        members = [s for s in shown if s["category"] == c]
        aggregates.append({
            "name": agg_key(c),
            "label": AGG_LABELS.get(c, f"热榜{c}"),
            "category": c,
            "items": sum(m["items"] for m in members),
            "sources": len(members),
        })

    return {"code": 200, "count": len(out), "shown": len(shown),
            "categories": cats, "aggregates": aggregates, "sources": out}


@app.get("/all")
def all_routes():
    with conn() as c, c.cursor() as cur:
        cur.execute("""
            select distinct s.name from sources s
            where s.engine = any(%s)
              and s.enabled and exists (select 1 from items i where i.source_id = s.id)
            order by s.name
        """, (ENGINES,))
        routes = [{"name": r["name"], "path": f"/{r['name']}"} for r in cur.fetchall()]
    return {"code": 200, "count": len(routes), "routes": routes}


def _to_item(r, idx):
    meta = r["meta"] or {}
    ts = meta.get("timestamp")
    if not isinstance(ts, (int, float)):
        try:
            ts = int(datetime.fromisoformat(str(ts)).timestamp() * 1000)
        except Exception:
            ts = int(r["last_seen"].timestamp() * 1000)
    heat = r.get("heat") or 0
    item = {
        "id": r["ext_id"] or idx,
        "title": r["title"],
        "desc": short_desc(meta.get("desc") or meta.get("hover") or meta.get("author") or ""),
        "cover": clean_cover(meta.get("cover") or ""),
        "timestamp": ts,
        "hot": int(heat) if heat else int(r.get("fallback_hot") or 0),
        "url": r["url"] or "",
        "mobileUrl": r["url"] or "",
        "rank": r.get("rank"),
        "engine": r["engine"],
        "index": idx,
        "firstSeen": r["first_seen"].isoformat() if r["first_seen"] else None,
    }
    # 聚合视图：每条标注来自哪个源（对标 rebang「每条下都有具体源的标记」）
    if r.get("src_name"):
        item["source"] = r.get("sid")
        item["sourceLabel"] = label_of(r["src_name"])
        also = [label_of(s) for s in dict.fromkeys(r.get("_also") or []) if s != r["src_name"]]
        if also:
            item["alsoIn"] = also
    return item


ITEM_COLS = f"""
    i.ext_id, i.title, i.url, i.meta, i.first_seen, i.last_seen,
    sn.rank as rank, sn.heat as heat, {HOT_EXPR} as fallback_hot, s.engine
"""


def _dedup_key(r) -> str:
    """去重键：**标题去掉所有标点/空白后归一化**（同一新闻在不同源的 URL 往往不同，
    只按 url 去重会漏），标题为空时退回 url。"""
    import re
    t = re.sub(r"[\W_]+", "", r["title"] or "").lower()
    return t or (r["url"] or "").strip().lower()


def _aggregate(cat: str, limit: int, cache: bool, order: str):
    """分类聚合视图：该分类下所有源的**最新一批榜单**合并去重，每条标注来源。

    order=heat（默认，按热度降序）｜order=source（各源轮转，保证每个源都有曝光）
    """
    from collections import deque

    with conn() as c, c.cursor() as cur:
        cur.execute(f"""
            with latest as (
                select i2.source_id as sid, max(sn.ts) as ts
                from snapshots sn
                join items i2 on i2.id = sn.item_id
                join sources s3 on s3.id = i2.source_id
                where s3.category = %s and s3.engine = any(%s)
                group by i2.source_id
            )
            select i.ext_id, i.title, i.url, i.meta, i.first_seen, i.last_seen,
                   sn.rank as rank, sn.heat as heat, {HOT_EXPR} as fallback_hot,
                   s.engine, s.name as src_name, s.id as sid
            from items i
            join sources s on s.id = i.source_id
            join snapshots sn on sn.item_id = i.id
            join latest l on l.sid = i.source_id and l.ts = sn.ts
            where s.category = %s and s.engine = any(%s)
            order by sn.heat desc nulls last, i.last_seen desc
            limit %s
        """, (cat, ENGINES, cat, ENGINES, max(limit * 6, 400)))
        rows = cur.fetchall()

    # ① 去重（保留热度最高的那条），同一条新闻被多个源收录的记进 _also
    uniq, index = [], {}
    for r in rows:
        k = _dedup_key(r)
        if k in index:
            index[k].setdefault("_also", []).append(r["src_name"])
            continue
        r["_also"] = []
        index[k] = r
        uniq.append(r)

    # ② 排序：heat=按热度（rows 本来就是热度序）｜source=各源轮转
    if order == "source":
        groups: dict[str, deque] = {}
        for r in uniq:
            groups.setdefault(r["src_name"], deque()).append(r)
        queues, picked = list(groups.values()), []
        while queues and len(picked) < limit:
            for q in list(queues):
                if q:
                    picked.append(q.popleft())
                if not q:
                    queues.remove(q)
                if len(picked) >= limit:
                    break
    else:
        picked = uniq[:limit]

    data = [_to_item(r, i + 1) for i, r in enumerate(picked)]
    srcs = sorted({r["src_name"] for r in rows})
    return {
        "code": 200,
        "name": agg_key(cat),
        "title": AGG_LABELS.get(cat, f"热榜{cat}"),
        "type": cat,
        "aggregate": True,
        "order": order,
        "engines": ENGINES,
        "raw": len(rows),          # 合并前条数
        "deduped": len(uniq),      # 合并后条数
        "sources": [{"name": s, "label": label_of(s)} for s in srcs],
        "total": len(data),
        "fromCache": bool(cache),
        "updateTime": int(datetime.now(BJ).timestamp() * 1000),
        "data": data,
    }


@app.get("/rising")
def rising(limit: int = 12, offset: int = 0):
    """📈 热点推荐（原"飙升榜"）：**归一化去重 + 多源共现 + 源内热度归一** 挑最热的条目。

    候选池：**只从 `RISING_CATS` 里的分类挑源**（2026-10-12 用户要求：不要从全部分类找，
    否则会刷到"游戏版本更新/装备补给"这类不是新闻的条目）。

    打分（跨源可比，解决各源热度口径差异巨大的问题）：
      ① 标题**归一化**（去标点/空白）后合并同一条新闻 → `cov` = 收录该新闻的源数量
      ② `pct` = 源内**排名百分位** `1 - (rank-1)/(n-1)`（0~1）—— 把"快手千万热度"和"虎扑几百热度"
         归一到同一尺度，等价于"相对所在源的热度"
      ③ `score = max(covcat-1, (cov-1)*0.5) + pct` → **跨分类共现优先**（越多源都在报 = 越真热点）
    代表条目取该新闻里 `pct` 最高（同分取 heat 最高）的那条。
    `offset` 用于「换一批」（翻到底自动回到开头）。
    """
    lim = max(1, min(limit, 50))
    off = max(0, offset)
    with conn() as c, c.cursor() as cur:
        # ⭐ 2026-10-22：这里原本用窗口函数在 142 万行 snapshots 上求「每源最新一批」
        #   （实测 0.78s，是首页最慢的一步）。current_items 已经是「每源当前批次」，
        #   直接读它 → 几千行、几毫秒。
        cur.execute(f"""
            with cnt as (   -- 每个源本批条目总数（用于算排名百分位）
                select source_id as sid, count(*) as n
                from current_items
                group by source_id
            )
            select ci.ext_id, ci.title, ci.url, ci.meta,
                   i.first_seen, i.last_seen,
                   ci.rank as rank, ci.heat as heat,
                   {HOT_EXPR} as fallback_hot, s.engine,
                   ci.source_id as sid, s.name as src_name, s.category,
                   1.0 - (ci.rank - 1)::numeric / greatest(cnt.n - 1, 1) as pct
            from current_items ci
            join items i on i.id = ci.item_id
            join sources s on s.id = ci.source_id
            join cnt on cnt.sid = ci.source_id
            where s.engine = any(%s) and s.category = any(%s) and ci.rank <= 30
            order by pct desc
        """, (ENGINES, RISING_CATS))
        rows = cur.fetchall()

    # 标题归一化合并：同一条新闻只留一个代表（pct 最高 / 同分 heat 最高），并统计共现源数
    groups = {}
    for r in rows:
        k = _dedup_key(r)
        g = groups.get(k)
        if g is None:
            groups[k] = {"best": r, "srcs": {r["src_name"]}, "cats": {r["category"]}}
        else:
            g["srcs"].add(r["src_name"])
            g["cats"].add(r["category"])
            a, b = g["best"], r
            if (b["pct"], b.get("heat") or 0) > (a["pct"], a.get("heat") or 0):
                g["best"] = b

    uniq = []
    for k, g in groups.items():
        r = dict(g["best"])
        r["_cov"] = len(g["srcs"])
        r["_covcat"] = len(g["cats"])
        # 跨**分类**共现算全分；同分类多源只算半分
        #   （否则同一批游戏公告会被 崩坏3/原神/米游社 等同分类源刷高共现数）
        r["_score"] = max(r["_covcat"] - 1, (r["_cov"] - 1) * 0.5) + float(r["pct"])
        uniq.append(r)
    # 排序：共现优先 → 归一化热度 → 原始热度
    uniq.sort(key=lambda r: (r["_score"], r["pct"], r.get("heat") or 0), reverse=True)

    total = len(uniq)
    if total == 0:
        return {"code": 200, "total": 0, "offset": 0, "nextOffset": 0, "items": []}
    # 多样性重排：同一源最多先出 3 条，其余挪到池尾 → 每批都不会被单个源刷屏
    per, head, tail = {}, [], []
    for r in uniq:
        n = per.get(r["src_name"], 0)
        (head if n < 3 else tail).append(r)
        per[r["src_name"]] = n + 1
    uniq = head + tail
    off %= total                                     # 翻到底自动回到开头
    picked = uniq[off:off + lim] or uniq[:lim]

    items = []
    for i, r in enumerate(picked, 1):
        it = _to_item(r, i)
        it["sourceName"] = r["src_name"]              # 供前端点击"切到该源"
        it["sourceLabel"] = label_of(r["src_name"])
        it["category"] = r["category"]
        it["coverage"] = r["_cov"]                     # 多源共现数
        it["pct"] = round(float(r["pct"]), 3)          # 源内归一化热度
        items.append(it)
    return {"code": 200, "total": total, "offset": off,
            "nextOffset": (off + lim) % total, "items": items}


@app.get("/{type_name}")
def hot(type_name: str, limit: int = 50, cache: bool = True, merge: int = 0, order: str = "heat"):
    """默认：主引擎那一版（**该源最新一次采集的榜单**，按源站名次）；merge=1：并集。

    type_name 形如 `zhihu` / `dailyhot:zhihu` / `agg:综合`（分类聚合视图，limit 默认给 100）。
    """
    if type_name.startswith("agg:"):
        return _aggregate(type_name[4:], max(1, min(limit, 300)), cache, order)
    if limit < 1 or limit > 200:
        limit = 50
    single = ":" in type_name
    engine, name = type_name.split(":", 1) if single else (None, type_name)

    with conn() as c, c.cursor() as cur:
        # 该源名下所有引擎行；**按最新一批榜单条数降序** → 第一条即主引擎（更完整的那份）
        # ⭐ 2026-10-21 性能修复：latest_items 原来是逐行相关子查询（140 万行 snapshots 重扫 → 每次
        #   ~3.9ms），而这里只命中 1~3 行，纯属白烧。改为「先定主引擎候选，再由 fetch_batch 里
        #   一次性算出 latest_ts」，排序退化为 last_ok_at（同一源多引擎时相差无几）。
        cur.execute("""
            select s.id, s.name, s.engine, s.category, s.last_ok_at
            from sources s
            where s.engine = any(%s) and s.enabled
              and ((%s::text is null and s.name = %s) or (s.id = %s))
            order by s.last_ok_at desc nulls last
        """, (ENGINES, engine, name, type_name))
        srcs = cur.fetchall()
        if not srcs:
            raise HTTPException(
                status_code=404,
                detail=f"未知源或该源不在启用引擎内: {type_name}（当前启用：{','.join(ENGINES)}）",
            )

        primary = srcs[0]

        # ⭐ 2026-10-21 性能修复：原先把 `LATEST_TS`（该源最新一批的时间戳）写成**相关子查询**
        #   放在 join 条件里，PostgreSQL 会对 items 的每一行重算一遍 —— 实测微博源被执行
        #   1290 次、每次 ~3.9ms，接口 5 秒才返回。
        # ⭐ 2026-10-22 Step 1：进一步改成**读物化表 current_items**（采集器每轮按源整体替换），
        #   读路径 = 一次索引扫描、零 join、不再算 max(ts)。老路径保留为兜底：
        #   新源在第一次采集成功前 current_items 里还没有行。
        def fetch_legacy(sid, cap):
            cur.execute(
                "select max(sn.ts) as ts from snapshots sn join items i2 on i2.id = sn.item_id "
                "where i2.source_id = %s",
                (sid,),
            )
            # 注意：本文件的 cursor 是 dict_row 工厂，必须按列名取值（row[0] 会 KeyError: 0）
            ts = (cur.fetchone() or {}).get("ts")
            if ts is None:
                return []
            cur.execute(f"""
                select {ITEM_COLS}
                from items i
                join sources s on s.id = i.source_id
                join snapshots sn on sn.item_id = i.id
                                 and sn.ts = %s
                where i.source_id = %s
                order by sn.rank nulls last, i.last_seen desc
                limit %s
            """, (ts, sid, cap))
            return cur.fetchall()

        def fetch_batch(sid, cap):
            cur.execute(f"""
                select ci.ext_id, ci.title, ci.url, ci.meta,
                       i.first_seen, i.last_seen,
                       ci.rank as rank, ci.heat as heat,
                       {HOT_EXPR} as fallback_hot, s.engine
                from current_items ci
                join items i on i.id = ci.item_id
                join sources s on s.id = ci.source_id
                where ci.source_id = %s
                order by ci.rank nulls last, i.last_seen desc
                limit %s
            """, (sid, cap))
            rows_ci = cur.fetchall()
            return rows_ci if rows_ci else fetch_legacy(sid, cap)

        rows = fetch_batch(primary["id"], max(limit * 2, 100))
        # merge=1：把其他引擎的独有条目追加在后（不混排）
        if merge and not single and len(srcs) > 1:
            for s2 in srcs[1:]:
                rows += fetch_batch(s2["id"], max(limit, 60))

    seen, data = set(), []
    for r in rows:
        dedup = (r["url"] or "").strip() or (r["title"] or "").strip().lower()
        if dedup in seen:
            continue
        seen.add(dedup)
        data.append(_to_item(r, len(data) + 1))
        if len(data) >= limit:
            break

    # updateTime 保持**拉取时间**（用户明确要求：不要改成真实数据批次时间）
    return {
        "code": 200,
        "name": type_name if single else primary["name"],
        "title": label_of(primary["name"]),
        "type": primary["category"],
        "primary": primary["engine"],
        "engines": [s["engine"] for s in srcs],
        "merged": bool(merge and not single),
        "link": "",
        "total": len(data),
        "fromCache": bool(cache),
        "updateTime": int(datetime.now(BJ).timestamp() * 1000),
        "data": data,
    }
