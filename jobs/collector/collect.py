#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""热榜采集器（P2）：两个引擎 → 归一化 → 幂等入库（items + snapshots）

设计约束（用户 2026-10-09 明确要求）：
  ⭐ **可插拔**：本文件不含任何「引擎专属」逻辑分支，只认 engines 配置里的 base_url/path。
     下线 dailyhot = 把它的 base_url 置空（或停容器），或把库里 sources.engine='dailyhot' 置 enabled=false。
     两种情况都**不需要改代码**，且历史数据一行不丢。
  ⭐ 某引擎不可达 → 整批跳过并记 last_err，**其余引擎照常入库**（不整轮失败）。

用法:
    .venv/bin/python collect.py                 # 正常一轮
    .venv/bin/python collect.py --init-schema   # 仅建表
    .venv/bin/python collect.py --bootstrap     # 建表 + 从 config 初始化 sources
    .venv/bin/python collect.py --engine dailyhot   # 只跑某个引擎（调试用）
    .venv/bin/python collect.py --dry-run       # 只抓不入库（看归一化结果）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import psycopg
import yaml

# ⭐ 时区统一 +8（北京）：全项目约定（见手册《时区规范》）
BJ = timezone(timedelta(hours=8))

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.yml")
SCHEMA = os.path.join(BASE, "schema.sql")
# 2026-10-12 工程化：宿主/容器/云服务器通用 —— 密码优先取环境变量，其次读文件
ENV_FILE = os.environ.get("HOTDB_ENV_FILE") or os.path.expanduser("~/Docker/hotdb/.env")
UA = "hotboard-collector/0.1 (+local)"

# ⭐ 2026-10-19 抓取逻辑规范化：自研源适配器（engine='custom'）
#   规范见 adapters/README.md —— **新增一个源 = 新增一个文件，不改本文件**。
if BASE not in sys.path:
    sys.path.insert(0, BASE)
import adapters                    # noqa: E402  （须在 sys.path 调整之后导入）
from adapters import new_client    # noqa: E402
import adapters.base as _adbase    # noqa: E402  （加固：robots.txt + 429/403 退避）

CUSTOM_ENGINE = "custom"           # 自研适配器统一使用的 engine 名（对应 sources.engine）

# ------------------------------------------------- 安全策略（robots / 限流退避）
# 2026-10-19 加固：
#   ① robots.txt —— 按域缓存规则，Disallow 的 URL 直接跳过（safety.respect_robots 开关，默认关）
#   ② 429/403 指数退避 —— 被限流时**不重试**，把该源冷却一段时间（首轮 base，逐次翻倍，封顶 max）
#   状态落在库表 source_backoff（不需要挂卷，重启不丢，排障可见）
BACKOFF_TABLE = """
create table if not exists source_backoff (
    source_id  text primary key,
    until      timestamptz not null,
    level      int         not null default 1,
    reason     text,
    updated_at timestamptz not null default now()
)
"""


def bump_backoff(conn, source_id: str, base_min: float, max_hours: float, reason: str) -> int:
    """把某源推进"限流冷却"：首轮 base_min 分钟，之后逐次翻倍，封顶 max_hours 小时。

    返回本轮冷却的**分钟数**（用于日志/展示）。
    ⚠️ 写库失败不能让整轮采集崩（否则一个源的退避问题会拖垮全部）→ 内部回滚并降级为"仅日志"。
    """
    row = conn.execute("select level from source_backoff where source_id=%s", (source_id,)).fetchone()
    level = (int(row[0]) + 1) if row else 1
    minutes = min(base_min * (2 ** (level - 1)), max_hours * 60)
    try:
        conn.execute(
            """insert into source_backoff (source_id, until, level, reason, updated_at)
               values (%s, now() + (%s || ' minutes')::interval, %s, %s, now())
               on conflict (source_id) do update
                 set until = excluded.until, level = excluded.level,
                     reason = excluded.reason, updated_at = now()""",
            (source_id, str(int(minutes)), level, reason[:120]))
    except Exception:                      # noqa: BLE001
        conn.rollback()                    # ⚠️ 否则连接卡在 aborted 事务
    return int(minutes)


# ---------------------------------------------------------------- 基础设施
def load_config() -> dict:
    """读 config.yml，并用**环境变量覆盖**关键项（同一份配置跨宿主/容器/云可用）"""
    with open(CONFIG, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    env = os.environ.get
    db = cfg.setdefault("db", {})
    if env("DB_HOST"):
        db["host"] = env("DB_HOST")
    _p = env("DB_PORT")
    if _p:
        db["port"] = int(_p)
    if env("DB_NAME"):
        db["dbname"] = env("DB_NAME")
    if env("DB_USER"):
        db["user"] = env("DB_USER")
    eng = cfg.setdefault("engines", {})
    if env("ENGINE_DAILYHOT_URL") is not None:
        eng.setdefault("dailyhot", {})["base_url"] = env("ENGINE_DAILYHOT_URL")
    if env("ENGINE_NEWSNOW_URL") is not None:
        eng.setdefault("newsnow", {})["base_url"] = env("ENGINE_NEWSNOW_URL")
    return cfg


def db_password() -> str:
    """密码来源优先级：环境变量 POSTGRES_PASSWORD > HOTDB_ENV_FILE 指向的文件 > 默认宿主路径"""
    if os.environ.get("POSTGRES_PASSWORD"):
        return os.environ["POSTGRES_PASSWORD"]
    with open(ENV_FILE, encoding="utf-8") as f:
        for line in f:
            if line.startswith("POSTGRES_PASSWORD="):
                return line.split("=", 1)[1].strip()
    raise SystemExit(f"未在环境变量或 {ENV_FILE} 找到 POSTGRES_PASSWORD")


SEED_CATEGORIES = os.path.join(BASE, "sql", "seed_categories.sql")
SEED_SORT_ORDER = os.path.join(BASE, "sql", "seed_sort_order.sql")


def seed_categories(conn) -> int:
    """应用分类种子（幂等）：**全新库**也能得到正确分类。

    为什么必须有：sources 的 category 决定前端分类栏与「热点推荐」候选池；
    全新部署如果只跑 bootstrap，所有源都会落到「其他」→ 前端分类栏与热点推荐都是空的。
    """
    if not os.path.exists(SEED_CATEGORIES):
        return 0
    with open(SEED_CATEGORIES, encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.strip().lower().startswith(("begin;", "commit;"))]
    with conn.cursor() as cur:
        cur.execute("".join(lines))
    conn.commit()
    return 1


def seed_sort_order(conn) -> int:
    """应用源默认排序（幂等）：**全新库**也能得到正确的源顺序。

    为什么必须有：`sources.sort_order` 为空时 api 按 `order by sort_order nulls last, name`
    排序 —— 会按名字拼音瞎排，把「今日头条热榜」排第一、知乎挤到第 14 位，
    而前端数据源标签默认只显示前几个 → 用户看不到知乎等头部源。
    """
    if not os.path.exists(SEED_SORT_ORDER):
        return 0
    with open(SEED_SORT_ORDER, encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.strip().lower().startswith(("begin;", "commit;"))]
    with conn.cursor() as cur:
        cur.execute("".join(lines))
    conn.commit()
    return 1


def apply_disabled_sources(conn, cfg) -> int:
    """把 config.yml 里 `disabled_sources` 列的源设为 enabled=false（幂等）。

    为什么要有：有些源从部署机**根本访问不到**（境外站出不了境、IP 被 WAF 封、
    需要 App 签名）。留着它们只会让前端列出一个个空榜单。
    改回来只需删掉 config.yml 对应行 —— 每次采集都会重新对齐。
    """
    srcs = cfg.get("disabled_sources") or []
    if not srcs:
        return 0
    with conn.cursor() as cur:
        cur.execute(
            "update sources set enabled = false "
            "where engine = 'custom' and src_id = any(%s) and enabled",
            (list(srcs),),
        )
        n = cur.rowcount
    conn.commit()
    return n


def connect(cfg: dict) -> psycopg.Connection:
    d = cfg["db"]
    return psycopg.connect(host=d["host"], port=d["port"], dbname=d["dbname"],
                           user=d["user"], password=db_password(), autocommit=False)


# ---------------------------------------------------------------- 归一化
def url_hash(source_id: str, url: str | None, ext_id: str | None) -> str:
    """去重键：优先用 url；没有 url 的源（如微博只有 id）用 源+引擎内 id 兜底"""
    key = (url or "").strip() or f"{source_id}:{ext_id or ''}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def title_sim(title: str) -> str:
    """极简 simhash（16 hex）：只用于跨源同题「候选」，真正合并留 P3 的 LLM 聚簇"""
    toks = [t for t in re.split(r"[\s\W_]+", title.lower()) if t]
    if not toks:
        toks = [title]
    v = [0] * 64
    for t in toks:
        h = int(hashlib.md5(t.encode("utf-8")).hexdigest()[:16], 16)
        for i in range(64):
            v[i] += 1 if (h >> i) & 1 else -1
    out = 0
    for i in range(64):
        if v[i] > 0:
            out |= 1 << i
    return f"{out:016x}"


def _num(x):
    """把 '1234.5万' / '1.2w' / 1234 / '3.2亿' 之类热度值转成 int（拿不到就 None）"""
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return int(x)
    s = str(x).strip().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([万亿wWkK]?)", s)
    if not m:
        return None
    v = float(m.group(1))
    unit = m.group(2)
    v *= {"万": 1e4, "w": 1e4, "W": 1e4, "亿": 1e8, "k": 1e3, "K": 1e3}.get(unit, 1)
    return int(v)


def normalize(engine: str, src_id: str, payload: dict, cover_base: str = "") -> list[dict]:
    """把两个引擎的响应统一成 [{ext_id,title,url,rank,heat,meta}]

    只处理"形状差异"，不做任何业务判断 —— 这是可插拔的关键。
    """
    rows: list[dict] = []
    # dailyhot: {"code":200,"name":"知乎","data":[{title,url,hot,...}]}
    if engine == "dailyhot" or ("data" in payload and isinstance(payload.get("data"), list)):
        for i, it in enumerate(payload.get("data") or [], 1):
            # 头图：多为绝对 URL；少数源（如少数派 banner）是相对路径 → 用 cover_base 补前缀
            cover = it.get("cover")
            if cover and cover_base and not str(cover).startswith("http"):
                cover = cover_base.rstrip("/") + "/" + str(cover).lstrip("/")
            meta = {k: it.get(k) for k in ("hot", "desc", "author", "timestamp")
                    if it.get(k) is not None}
            if cover:
                meta["cover"] = cover
            rows.append({
                "ext_id": str(it.get("id") or it.get("url") or i),
                "title": (it.get("title") or "").strip(),
                "url": it.get("url") or it.get("mobileUrl"),
                "rank": i,
                "heat": _num(it.get("hot") or it.get("heat") or it.get("num")),
                "meta": meta,
            })
    # newsnow: {"status":"success","items":[{id,title,url,extra}]}
    elif "items" in payload:
        for i, it in enumerate(payload.get("items") or [], 1):
            extra = it.get("extra") or {}
            rows.append({
                "ext_id": str(it.get("id") or i),
                "title": (it.get("title") or "").strip(),
                "url": it.get("url") or (extra.get("url") if isinstance(extra, dict) else None),
                "rank": i,
                "heat": _num(extra.get("info") if isinstance(extra, dict) else None),
                "meta": {"extra": extra, "source": it.get("source")},
            })
    return [r for r in rows if r["title"]]


# ---------------------------------------------------------------- 抓取
def fetch(url: str, timeout: int, retries: int, retry_wait: float):
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace")), None
        except Exception as e:                       # noqa: BLE001 统一记错，不区分类型
            last = f"{type(e).__name__}: {str(e)[:80]}"
            if attempt < retries:
                time.sleep(retry_wait)
    return None, last


def reachable(url: str, timeout: int = 8) -> tuple[bool, str | None]:
    """引擎可达性预检：只要**拿到 HTTP 响应**就算活（根路径返回 HTML 也算）。

    这里刻意不要求 JSON —— dailyhot 的 / 是落地页、newsnow 的 / 是 SPA，
    都返回 HTML；只有连不上/超时才算引擎不可达。
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            _ = r.read(512)
        return True, None
    except urllib.error.HTTPError as e:              # 有响应（4xx/5xx）→ 服务在跑
        return True, f"HTTP {e.code}"
    except Exception as e:                           # noqa: BLE001 连接层失败才算不可达
        return False, f"{type(e).__name__}: {str(e)[:60]}"


# ---------------------------------------------------------------- 主流程
def init_schema(conn) -> None:
    with open(SCHEMA, encoding="utf-8") as f:
        conn.execute(f.read())
    conn.commit()


def bootstrap_sources(conn, cfg) -> int:
    """首轮初始化 sources 表（幂等）

    两个来源：
      ① 外部引擎（dailyhot / newsnow）—— 读 config.yml 的 `bootstrap:` 段
         ⚠️ 2026-11-06：这两个引擎早已移除，config.yml 里那段 61 个源的清单也删了。
         这里保留分支但**只处理 ENGINE_WHITELIST 内的引擎**，防止有人再往 config 里
         加外部引擎清单、又在库里攒出一批「从未成功、0 数据」的残留行。
      ② 自研适配器（custom）—— **自动扫描 adapters/ 目录**，
         name / category 直接从适配器模块里取，不用手工维护源清单
    """
    n = 0
    whitelist = _engine_whitelist()

    # ① 外部引擎（仅白名单内；白名单只有 custom 时这段直接跳过）
    for engine, srcs in (cfg.get("bootstrap") or {}).items():
        if engine not in whitelist:
            if srcs:
                print(f"  ⚠️ bootstrap 段里的 `{engine}` 不在 ENGINE_WHITELIST "
                      f"({','.join(whitelist)})，已跳过 {len(srcs)} 个源")
            continue
        for s in srcs:
            sid = f"{engine}:{s}"
            cur = conn.execute(
                """insert into sources (id, engine, src_id, name, category)
                   values (%s, %s, %s, %s, %s) on conflict (id) do nothing""",
                (sid, engine, s, s, None))
            n += cur.rowcount

    # ② 自研适配器：自动发现，避免新部署漏源
    for spec in adapters.specs():
        sid = f"custom:{spec['src_id']}"
        cur = conn.execute(
            # on conflict (id) do update：适配器里改了 NAME / CATEGORY 之后，
            # 已存在的库也要跟着更新。原来 do nothing，导致改分类对线上库完全无效
            # （实测「财经」只有 1 个源就是这个坑）。
            """insert into sources (id, engine, src_id, name, category)
               values (%s, 'custom', %s, %s, %s)
               on conflict (id) do update
                 set name = excluded.name,
                     category = excluded.category,
                     src_id = excluded.src_id""",
            (sid, spec["src_id"], spec["name"], spec["category"]))
        n += cur.rowcount

    conn.commit()
    return n


def prune_legacy_engines(conn) -> int:
    """清掉「已废弃引擎」的残留源行（幂等，安全条件卡得很死）。

    dailyhot / newsnow 两个外部引擎已经移除，但 `sources` 表里还留着 61 行
    （dailyhot 31 + newsnow 30），全部 `last_ok_at is null`、`items_seen = 0`、
    `items` 表里 0 条 —— 只会污染分类统计（把"综合"从 12 撑到 43）。

    只删同时满足以下全部条件的行，任何一条不满足就不动：
      1. engine 不在 ENGINE_WHITELIST 内
      2. items_seen = 0（从没抓到过）
      3. last_ok_at is null（从没成功过）
      4. items / current_items 里没有引用（有数据就保留，交给人工判断）

    返回删除行数。
    """
    whitelist = _engine_whitelist()
    rows = conn.execute(
        """select s.id, s.engine, s.src_id, s.name
             from sources s
            where not (s.engine = any(%s))
              and coalesce(s.items_seen, 0) = 0
              and s.last_ok_at is null
              and not exists (select 1 from items i where i.source_id = s.id)
              and not exists (select 1 from current_items c where c.source_id = s.id)""",
        (whitelist,)).fetchall()
    if not rows:
        return 0
    ids = [r[0] for r in rows]
    conn.execute("delete from sources where id = any(%s)", (ids,))
    conn.commit()
    engines = {}
    for r in rows:
        engines[r[1]] = engines.get(r[1], 0) + 1
    detail = " / ".join(f"{e} {c} 行" for e, c in sorted(engines.items()))
    print(f"  🧹 清理废弃引擎残留源: {len(ids)} 行（{detail}）")
    return len(ids)


def _engine_whitelist() -> list:
    """当前启用的引擎白名单（与 API 的 ENGINE_WHITELIST 同一个环境变量）"""
    raw = os.getenv("ENGINE_WHITELIST", "custom")
    return [e.strip() for e in raw.split(",") if e.strip()]


def crawl(conn, cfg, only_engine=None, dry_run=False) -> dict:
    # ⭐ 时区统一 +8（北京）：批次时间戳按北京时间取整（快照 ts 是 timestamptz，显示即 +8）
    started = datetime.now(BJ)
    stats = defaultdict(lambda: {"ok": 0, "err": 0, "items": 0})
    new = upd = snaps = errs = 0

    engines = cfg["engines"]
    rate = cfg.get("rate") or {}
    min_interval = 1.0 / float(rate.get("max_per_second") or 1)
    retries = int(rate.get("retries") or 0)
    retry_wait = float(rate.get("retry_wait") or 3)

    # ⭐ 自研源：走适配器注册表（与外部引擎共用同一个数据契约 Item）
    adapter_mods = adapters.all_adapters()
    _ac = cfg.get("adapters") or {}
    client = new_client(timeout=int(_ac.get("timeout") or 25), retries=retries,
                        retry_wait=retry_wait, min_interval=min_interval)

    # ⭐ 安全策略：robots 尊重 + 限流退避（2026-10-19 加固，可配置关闭）
    safety = cfg.get("safety") or {}
    _adbase.RESPECT_ROBOTS = bool(safety.get("respect_robots", False))
    bo_base_min = float(safety.get("backoff_base_min", 30))
    bo_max_hours = float(safety.get("backoff_max_hours", 24))
    # ⚠️ 建表**任何时候都做**（幂等 DDL）：dry-run 也要建，否则下面的 select 报
    #    "relation does not exist" → 事务 abort → 后续所有 SQL 报 InFailedSqlTransaction
    #    （2026-10-19 实际踩过：dry-run 直接崩在这一步）
    conn.execute(BACKOFF_TABLE)
    conn.commit()
    cooling: dict[str, str] = {}
    try:
        for r in conn.execute("select source_id, until, level, reason from source_backoff "
                              "where until > now()").fetchall():
            cooling[r[0]] = f"限流冷却至 {r[1]:%H:%M}（level={r[2]}, {r[3] or ''}）"
    except Exception:                      # noqa: BLE001
        conn.rollback()                    # ⚠️ 必须回滚，否则连接会卡在 aborted 事务里
        cooling = {}

    # 引擎可达性预检：不可达 → 整批跳过（不影响其他引擎）
    live = {}
    for eng, ec in engines.items():
        base = (ec.get("base_url") or "").strip()
        if only_engine and eng != only_engine:
            live[eng] = False
            continue
        if not base:
            print(f"  ⏭️  引擎 {eng} 未配置 base_url → 跳过（可插拔）")
            live[eng] = False
            continue
        ok, why = reachable(base, timeout=8)
        live[eng] = ok
        if not live[eng]:
            print(f"  ❌ 引擎 {eng} 不可达（{why}）→ 该引擎的源整批跳过，其余照常")
            stats[eng]["err"] += 1

    # ⭐ 自研源无需 HTTP 上游预检：适配器自己负责可达性与响应形状校验
    live[CUSTOM_ENGINE] = only_engine in (None, CUSTOM_ENGINE)

    rows = conn.execute(
        "select id, engine, src_id from sources where enabled order by engine, id").fetchall()

    last_req = 0.0
    ts = started.replace(second=0, microsecond=0)
    skipped = 0
    robots_skips = 0
    robots_allow = {str(s).strip() for s in (safety.get("robots_allowlist") or [])}
    for sid, engine, src_id in rows:
        if not live.get(engine):
            continue

        # ⭐ 限流冷却中的源：本轮直接跳过（不计入错误，避免噪音淹没真实故障）
        if sid in cooling:
            skipped += 1
            print(f"  ⏸️  {sid:<28} {cooling[sid]}")
            continue

        # ⭐ robots 白名单例外：只对显式声明的 src_id 关闭 robots 检查（默认全部遵守）
        _adbase.RESPECT_ROBOTS = bool(safety.get("respect_robots", False)) and (src_id not in robots_allow)

        # ⭐ 自研源（engine='custom'）→ 走适配器；其余 → 原 HTTP 上游路径（行为不变）
        if engine == CUSTOM_ENGINE:
            mod = adapter_mods.get(src_id)
            fetch_fn = getattr(mod, "fetch", None) if mod is not None else None
            if fetch_fn is None:
                stats[engine]["err"] += 1
                errs += 1
                msg = f"未找到适配器 adapters/{src_id}.py"
                if not dry_run:
                    conn.execute("update sources set last_err=%s, updated_at=now() where id=%s",
                                 (msg, sid))
                print(f"  ❌ {sid:<28} {msg}")
                continue
            try:
                items = [it.as_row() for it in fetch_fn(client)]
                err = None
            except _adbase.RobotsDisallowed:
                # ⭐ 合规：robots.txt 明确禁止 → 跳过并如实记录（**不算错误**，否则每轮都误报）
                items, err = None, "__ROBOTS__"
            except _adbase.RateLimited as e:
                # ⭐ 被限流：不重试，进指数退避冷却（并记进 sources.last_err）
                mins = bump_backoff(conn, sid, bo_base_min, bo_max_hours, f"HTTP {e.status}")
                items, err = None, f"被限流(HTTP {e.status})，冷却 {mins} 分钟后自动恢复"
            except Exception as e:            # noqa: BLE001 —— 适配器异常统一记源级错误
                items, err = None, f"{type(e).__name__}: {str(e)[:80]}"
        else:
            base = (engines[engine].get("base_url") or "").rstrip("/")
            path = (engines[engine].get("path") or "/{src}").replace("{src}", src_id)
            url = base + path
            wait = min_interval - (time.time() - last_req)
            if wait > 0:
                time.sleep(wait)
            payload, err = fetch(url, int(engines[engine].get("timeout") or 25), retries, retry_wait)
            last_req = time.time()
            items = None
            if not err and payload:
                items = normalize(engine, src_id, payload,
                                  (engines.get(engine) or {}).get("cover_base", {}).get(src_id, ""))

        if err or items is None:
            if err == "__ROBOTS__":
                # 合规跳过：单独计数，用 🚫 标记（cron 脚本只 grep ❌，不会误报微信）
                robots_skips += 1
                if not dry_run:
                    conn.execute("update sources set last_err=%s, updated_at=now() where id=%s",
                                 ("robots.txt 禁止抓取（合规跳过；如需例外请加入 "
                                  "config.yml safety.robots_allowlist）", sid))
                print(f"  🚫 {sid:<28} robots.txt 禁止抓取（合规跳过）")
                continue
            stats[engine]["err"] += 1
            errs += 1
            if not dry_run:
                conn.execute("update sources set last_err=%s, updated_at=now() where id=%s", (err, sid))
            print(f"  ❌ {sid:<28} {err}")
            continue
        stats[engine]["ok"] += 1
        stats[engine]["items"] += len(items)
        if dry_run:
            print(f"  🔎 {sid:<28} {len(items):>4} 条  例: {items[0]['title'][:30] if items else '-'}")
            continue

        for it in items:
            h = url_hash(sid, it["url"], it["ext_id"])
            cur = conn.execute(
                """insert into items (source_id, ext_id, title, url, url_hash, title_sim, meta)
                   values (%s,%s,%s,%s,%s,%s,%s)
                   on conflict (source_id, url_hash) do update
                     set last_seen = now(), title = excluded.title, meta = excluded.meta
                   returning (xmax = 0) as inserted""",
                (sid, it["ext_id"], it["title"], it["url"], h, title_sim(it["title"]),
                 json.dumps(it["meta"], ensure_ascii=False)))
            rid = cur.fetchone()
            item_id = conn.execute("""select id from items where source_id=%s and url_hash=%s""",
                                   (sid, h)).fetchone()[0]
            if rid and rid[0]:
                new += 1
            else:
                upd += 1
            cur2 = conn.execute(
                """insert into snapshots (item_id, ts, rank, heat) values (%s,%s,%s,%s)
                   on conflict (item_id, ts) do nothing""",
                (item_id, ts, it["rank"], it["heat"]))
            snaps += cur2.rowcount
        conn.execute("delete from source_backoff where source_id=%s", (sid,))
        conn.execute("update sources set last_ok_at=now(), last_err=null, items_seen=%s, "
                     "updated_at=now() where id=%s", (len(items), sid))
        # ⭐ 2026-10-22：维护「当前榜单」物化表 —— 每轮按源**整体替换**（同一事务内），
        #   读路径从"扫 140 万行 snapshots 算最新一批"变成一次索引扫描（API 端零 join）。
        #   失败时整体回滚，不会出现半新半旧。
        try:
            conn.execute("delete from current_items where source_id=%s", (sid,))
            conn.execute("""
                insert into current_items
                       (source_id, item_id, rank, heat, ts, title, url, ext_id, meta)
                select i.source_id, i.id, sn.rank, sn.heat, sn.ts,
                       i.title, i.url, i.ext_id, i.meta
                from snapshots sn
                join items i on i.id = sn.item_id
                where i.source_id = %s and sn.ts = %s
                on conflict (source_id, item_id) do update
                  set rank = excluded.rank, heat = excluded.heat, ts = excluded.ts,
                      title = excluded.title, url = excluded.url, meta = excluded.meta
            """, (sid, ts))
        except Exception as e:      # 物化失败不该拖垮整轮采集（真值仍在 items/snapshots）
            print(f"  ⚠️  current_items 维护失败（{sid}）: {type(e).__name__}: {e}")
            conn.rollback()
            raise
        print(f"  ✅ {sid:<28} {len(items):>4} 条")
    conn.commit()

    if skipped:
        print(f"  ⏸️  本轮因限流冷却跳过 {skipped} 个源（冷却期满自动恢复）")
    if robots_skips:
        print(f"  🚫 本轮因 robots.txt 合规跳过 {robots_skips} 个源"
              f"（如需例外：config.yml safety.robots_allowlist）")

    summary = {"items_new": new, "items_upd": upd, "snapshots": snaps, "errors": errs,
               "skipped": skipped, "robots_skipped": robots_skips,
               "engines": {k: dict(v) for k, v in stats.items()}}
    if not dry_run:
        conn.execute("""insert into crawl_runs (started_at, finished_at, engine_stats,
                        items_new, items_upd, snapshots, errors)
                        values (%s, now(), %s, %s, %s, %s, %s)""",
                     (started, json.dumps(summary["engines"], ensure_ascii=False),
                      new, upd, snaps, errs))
        conn.commit()
    return summary


def maintain_db():
    """每日库维护：补齐未来分区 / 删掉 90 天前的分区 / 清理 180 天没再出现的 items。

    依赖 migrations/20261022_step2_partition_snapshots.sql 里建的 hotboard_maintain()；
    函数不存在（还没做分区迁移）就安静跳过 —— 不影响采集。
    """
    cfg = load_config()
    with connect(cfg) as conn:
        row = conn.execute(
            "select to_regprocedure('hotboard_maintain(integer,integer)') as f").fetchone()
        if not row or not row[0]:
            print("ℹ️  未安装分区维护函数（跳过；见 jobs/collector/migrations/）", flush=True)
            return
        rows = conn.execute("select action, detail from hotboard_maintain()").fetchall()
        conn.commit()
        if not rows:
            print("🧹 库维护：无需变更", flush=True)
        for r in rows:
            print(f"🧹 库维护 {r[0]}: {r[1]}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--init-schema", action="store_true")
    ap.add_argument("--bootstrap", action="store_true")
    ap.add_argument("--engine", default=None, help="只跑某个引擎")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--seed-categories", action="store_true",
                    help="只应用分类种子（幂等；全新库/改分类后同步用）")
    # 2026-10-12 工程化：容器常驻模式（云服务器/一键部署时用；本机仍由 Hermes cron 触发 --once）
    ap.add_argument("--loop", action="store_true", help="常驻：每 --interval 秒跑一轮（默认读 COLLECT_INTERVAL_SEC）")
    ap.add_argument("--interval", type=int,
                    default=int(os.environ.get("COLLECT_INTERVAL_SEC") or 1800),
                    help="--loop 模式下的间隔秒数（默认 1800 = 30 分钟）")
    a = ap.parse_args()

    if a.loop:
        print(f"🔁 采集器常驻模式：每 {a.interval}s 一轮（Ctrl-C 退出）", flush=True)
        last_maintain = None      # ⭐ 每天跑一次库维护（分区/保留策略）
        # 全新库「零手工启动」：常驻模式的第一轮先建表 + 灌源 + 应用分类/排序种子。
        # 原来只有显式 --bootstrap 才做这些，导致新部署必须手工再跑一条命令，
        # 否则 sources 表是空的、前端一个源都没有。全部幂等，重复启动无副作用。
        first_round = True
        while True:
            try:
                a.init_schema = first_round
                a.bootstrap = first_round
                if last_maintain != datetime.now().date():
                    try:
                        maintain_db()
                        last_maintain = datetime.now().date()
                    except Exception as e:      # 维护失败不影响采集
                        print(f"⚠️  库维护失败：{type(e).__name__}: {e}", flush=True)
                run_once(a)
                first_round = False
            except KeyboardInterrupt:
                print("⏹ 收到中断，退出", flush=True)
                return 0
            except Exception as e:  # 常驻模式不因单轮异常退出
                print(f"❌ 本轮异常：{type(e).__name__}: {e}", flush=True)
            time.sleep(a.interval)

    run_once(a)
    return 0


def run_once(a):
    cfg = load_config()
    print(f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} 热榜采集开始", flush=True)
    with connect(cfg) as conn:
        if a.init_schema or a.bootstrap or getattr(a, "seed_categories", False):
            init_schema(conn)
            print("  ✅ 库表就绪", flush=True)
        if a.bootstrap:
            n = bootstrap_sources(conn, cfg)
            # upsert 的 rowcount 把「更新」也算进去，别误导成"新增 69 行"；这里报处理条数
            print(f"  ✅ sources 同步完成（处理 {n} 条源记录，幂等）", flush=True)
            # 清掉已废弃引擎的残留行（dailyhot/newsnow），新库上是 0 行、无操作；
            # 老库上把历史残留顺手清干净，不用再手工跑 SQL
            pruned = prune_legacy_engines(conn)
            if pruned:
                print(f"  ✅ 废弃引擎残留已清理（{pruned} 行）", flush=True)
            seed_categories(conn)
            print("  ✅ 分类种子已应用（幂等）", flush=True)
            if seed_sort_order(conn):
                print("  ✅ 源默认排序已应用（幂等）", flush=True)
        elif getattr(a, "seed_categories", False):
            seed_categories(conn)
            print("  ✅ 分类种子已应用（幂等）", flush=True)
        s = crawl(conn, cfg, only_engine=a.engine, dry_run=a.dry_run)
        # 把 config.yml 里声明为「不可达」的源关掉（幂等，每轮对齐一次）
        off = apply_disabled_sources(conn, cfg)
        if off:
            print(f"  ⏸️  已停用不可达源 {off} 个（config.yml: disabled_sources）", flush=True)
    print(f"📊 新增 {s['items_new']} / 更新 {s['items_upd']} / 快照 {s['snapshots']} / 错误 {s['errors']}", flush=True)
    for eng, st in s["engines"].items():
        print(f"   {eng}: 源成功 {st['ok']} 失败 {st['err']} 抓到 {st['items']} 条", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
