#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""源适配器契约（抓取逻辑规范化的地基）

设计目标（用户 2026-10-19）：
    后续会持续新增源，所以抓取逻辑必须规范 —— 新增一个源 = **新增一个文件**，不改核心代码。

三条不可妥协的规矩：
  1. ⭐ **heat 拿不到就是 None**：严禁填 0/假值 —— snapshots.heat 是涨跌护城河，被污染就废了
  2. **fetch() 只做「取 + 解析」，禁止碰数据库**：入库统一由 collect.py 负责（可 dry-run、可单测）
  3. **ext_id 必须跨轮次稳定**：否则 items 的 first_seen/last_seen 与去重键全乱

用法（写一个自研源）：
    # adapters/<src_id>.py
    SRC_ID, NAME, CATEGORY = "xueqiu", "雪球", "综合"
    def fetch(client):
        payload = client.get_json("https://.../listV2.json", headers={...})
        return [Item(ext_id=str(x["id"]), title=x["title"].strip(), url=x.get("target"),
                     desc=x.get("description"), heat=num(x.get("hot"))) for x in payload["items"]]
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import re
import socket
import subprocess
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Protocol, runtime_checkable

# 抓取用 UA：多数站点（steam/豆瓣/凤凰/金十等）会拦爬虫 UA，故用桌面浏览器 UA。
# 移植自 newsnow（MIT）的默认 UA；礼貌抓取仍由 HttpClient 的全局限速保证，未放松。
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
# 本地标识（仅用于我们自己打点的场景，如需要）
UA_LOCAL = "hotboard-collector/0.1 (+local)"

# ⭐ 2026-10-21 云端适配：腾讯云等机房**默认没有 IPv6 路由**，而 v2ex / hackernews /
#   nodeseek / nytimes 会先解析到 AAAA → 直接 `Network is unreachable`（实测 4 源必挂）。
#   这里全局把 getaddrinfo 收敛为 IPv4 优先，个别源真需要 IPv6 时用
#   `HOTBOARD_FORCE_IPV4=0` 关掉。本机（家宽双栈）保留默认，不受影响。
if os.environ.get("HOTBOARD_FORCE_IPV4", "1") != "0":
    _orig_getaddrinfo = socket.getaddrinfo

    def _ipv4_first(host, port, family=0, type=0, proto=0, flags=0):
        infos = _orig_getaddrinfo(host, port, family, type, proto, flags)
        v4 = [i for i in infos if i[0] == socket.AF_INET]
        return v4 or infos

    socket.getaddrinfo = _ipv4_first


# ---------------------------------------------------------------- 数据契约
@dataclass
class Item:
    """一个榜单条目（所有适配器的统一输出）。

    rank 由「返回顺序」决定（第 1 条 = rank 1），适配器不要自行打乱。
    heat 拿不到就留 None —— 不许填 0。
    """
    ext_id: str
    title: str
    url: str | None = None
    rank: int | None = None
    heat: int | None = None
    desc: str | None = None
    cover: str | None = None
    author: str | None = None
    timestamp: int | None = None
    extra: dict | None = None

    def as_row(self) -> dict:
        """转成 collect.py 入库循环使用的行结构（与历史数据形状一致）。

        注意 meta 的键与既有数据保持一致：hot / desc / cover / author / timestamp。
        """
        meta: dict = {}
        if self.heat is not None:
            meta["hot"] = self.heat
        if self.desc:
            meta["desc"] = self.desc
        if self.cover:
            meta["cover"] = self.cover
        if self.author:
            meta["author"] = self.author
        if self.timestamp:
            meta["timestamp"] = self.timestamp
        if self.extra:
            meta["extra"] = self.extra
        return {
            "ext_id": str(self.ext_id),
            "title": (self.title or "").strip(),
            "url": self.url,
            "rank": self.rank,
            "heat": self.heat,
            "meta": meta,
        }


def num(x) -> int | None:
    """把 '1234.5万' / '1.2w' / '3.2亿' / 1234 转成 int；拿不到返回 None（绝不返回 0 冒充热度）。"""
    if x is None:
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return int(x)
    s = str(x).strip().replace(",", "")
    m = re.match(r"^([\d.]+)\s*([万亿wWkK]?)", s)
    if not m:
        return None
    v = float(m.group(1))
    v *= {"万": 1e4, "w": 1e4, "W": 1e4, "亿": 1e8, "k": 1e3, "K": 1e3}.get(m.group(2), 1)
    return int(v)


def clip(s, n: int = 400) -> str | None:
    """描述类字段统一截断，避免把整篇正文塞进 meta。"""
    if not s:
        return None
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s[:n] if s else None


def ts_ms(x, tz_hours: int = 8) -> int | None:
    """时间戳归一化（移植 DailyHotApi `getTime()` 的语义，但**返回秒**，与项目其它字段一致）。

    - 数字/纯数字串：> 946684800000 视为已是毫秒 → 转秒；否则按秒。
    - 字符串：先试标准格式（含 ISO），再试中文相对时间（N分钟前 / N小时前 / 昨天 HH:mm /
      今天 HH:mm / M月D日 [HH:mm] / HH:mm）；失败返回 None（**不返回 0，避免污染**）。
    """
    import time as _t
    if x is None or x == "":
        return None
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        v = int(x)
        return v // 1000 if v > 946684800000 else v
    s = str(x).strip()
    if not s:
        return None
    if re.fullmatch(r"\d{9,19}", s):
        v = int(s)
        return v // 1000 if v > 946684800000 else v
    # 标准格式优先
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M", "%Y/%m/%d", "%Y-%m-%d-%H"):
        try:
            return int(datetime.strptime(s[:19], fmt).replace(
                tzinfo=timezone(timedelta(hours=tz_hours))).timestamp())
        except Exception:  # noqa: BLE001
            continue
    # ISO（带 T / Z 偏移）
    try:
        return int(datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp())
    except Exception:  # noqa: BLE001
        pass
    # 中文相对时间
    now = datetime.now(timezone(timedelta(hours=tz_hours)))
    m = re.fullmatch(r"(\d+)\s*(分钟|小时|天)前", s)
    if m:
        n = int(m.group(1)) * {"分钟": 60, "小时": 3600, "天": 86400}[m.group(2)]
        return int(now.timestamp()) - n
    m = re.fullmatch(r"(昨天|今天)\s*(\d{1,2}):(\d{2})", s)
    if m:
        base = now if m.group(1) == "今天" else now - timedelta(days=1)
        return int(base.replace(hour=int(m.group(2)), minute=int(m.group(3)),
                                second=0, microsecond=0).timestamp())
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)                    # 只给时间 → 当今天
    if m:
        return int(now.replace(hour=int(m.group(1)), minute=int(m.group(2)),
                               second=0, microsecond=0).timestamp())
    m = re.fullmatch(r"(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2}))?", s)
    if m:
        return int(now.replace(month=int(m.group(1)), day=int(m.group(2)),
                               hour=int(m.group(3) or 0), minute=int(m.group(4) or 0),
                               second=0, microsecond=0).timestamp())
    return None


def cn_num(x) -> int | None:
    """中文单位数字：'1.2亿' → 120000000；'3456万' → 34560000；'956' → 956。

    移植 DailyHotApi `parseChineseNumber()`；空/无法解析 → None（**绝不返回 0**）。
    """
    if x is None or x == "":
        return None
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return int(x)
    s = str(x).strip().replace(",", "")
    if not s:
        return None
    m = re.match(r"^([\d.]+)\s*([亿万千百wWkK]?)", s)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    v *= {"亿": 1e8, "万": 1e4, "w": 1e4, "W": 1e4, "千": 1e3, "k": 1e3, "K": 1e3,
          "百": 1e2}.get(m.group(2), 1)
    out = int(v)
    return out if out else None


def epoch_sec(x, tz_hours: int = 8) -> int | None:
    """给明确知道是"秒/毫秒"的时间用（同 ts_ms，但语义更直白）。"""
    return ts_ms(x, tz_hours)


def strip_html(s) -> str | None:
    if not s:
        return None
    return re.sub(r"<[^>]+>", "", str(s)).strip() or None


def parse_rss(raw: str) -> list[dict]:
    """通用 RSS 2.0 / Atom 解析（公开 feed 类源共用）。

    返回 [{title, link, guid, desc, author, pub, cover}]；解析不出任何条目时返回 []。
    - RSS 2.0：item/title,link,guid,description,pubDate,dc:creator/author
    - Atom：entry/title,link[href],id,summary|content,updated|published,author/name
    - 封面：enclosure / media:thumbnail / media:content / itunes:image，或正文首个 <img src>
    """
    out: list[dict] = []
    try:
        root = ET.fromstring(raw)
    except Exception:  # noqa: BLE001
        return out

    def _t(node, *tags) -> str:
        for tag in tags:
            el = node.find(tag)
            if el is not None and (el.text or "").strip():
                return (el.text or "").strip()
            if el is not None:                       # Atom link 用 href
                for attr in ("href", "url"):
                    if el.get(attr):
                        return el.get(attr, "").strip()
        return ""

    def _cover(node, desc: str) -> str | None:
        for tag in ("enclosure", "{http://search.yahoo.com/mrss/}thumbnail",
                    "{http://search.yahoo.com/mrss/}content",
                    "{http://www.itunes.com/dtds/podcast-1.0.dtd}image"):
            el = node.find(tag)
            if el is not None and el.get("url"):
                return el.get("url")
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc or "", re.I)
        return m.group(1) if m else None

    for node in list(root.findall(".//item")) + list(root.findall(".//{http://www.w3.org/2005/Atom}entry")):
        title = _t(node, "title", "{http://www.w3.org/2005/Atom}title")
        link = _t(node, "link", "{http://www.w3.org/2005/Atom}link")
        desc = _t(node, "description", "{http://www.w3.org/2005/Atom}content",
                  "{http://www.w3.org/2005/Atom}summary")
        out.append({
            "title": title,
            "link": link,
            "guid": _t(node, "guid", "{http://www.w3.org/2005/Atom}id"),
            "desc": desc,
            "author": _t(node, "{http://purl.org/dc/elements/1.1/}creator", "author",
                         "{http://www.w3.org/2005/Atom}author"),
            "pub": _t(node, "pubDate", "{http://www.w3.org/2005/Atom}updated",
                      "{http://www.w3.org/2005/Atom}published"),
            "cover": _cover(node, desc),
        })
    return out


# ------------------------------------------------- 安全策略（robots / 限流退避）
class RateLimited(Exception):
    """源站返回 429/403（限流或封禁）。collect.py 据此做指数退避并暂时停该源。

    为什么不在这里重试：重试 429 正是**加剧**封锁的行为（DailyHotApi/newsnow 都不做退避）。
    """

    def __init__(self, status: int, url: str = ""):
        self.status = status
        self.url = url
        super().__init__(f"HTTP {status}（限流/拒绝）{url[:70]}")


class RobotsDisallowed(Exception):
    """robots.txt 明确禁止抓取该 URL（合规起见直接跳过，不重试）。"""


# 默认关闭：由 collect.py 按 config 的 safety.respect_robots 打开，
# 避免"改了 base.py 却没人知道行为变了"。
RESPECT_ROBOTS = False
_robots_cache: dict = {}


def robots_allows(url: str, timeout: float = 6.0) -> bool:
    """按域缓存 robots.txt 判定是否允许抓取；取不到（超时/404/异常）一律**放行**（fail-open）。

    缓存粒度是"域"，一个进程内同一站只取一次 robots.txt。
    """
    import urllib.parse as _up
    import urllib.robotparser as _rp

    parts = _up.urlsplit(url)
    base = f"{parts.scheme}://{parts.netloc}"
    if base in _robots_cache:
        rp = _robots_cache[base]
        return True if rp is None else rp.can_fetch(UA, url)
    rp = None
    try:
        req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if getattr(r, "status", 200) == 200:
                rp = _rp.RobotFileParser()
                rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except Exception:  # noqa: BLE001 —— robots 拿不到不等于禁止
        rp = None
    _robots_cache[base] = rp
    return True if rp is None else rp.can_fetch(UA, url)


# ---------------------------------------------------------------- HTTP 客户端
class HttpClient:
    """统一出口：UA / 超时 / 重试 / 全局限速都在这里。

    规范：适配器**不要**自己建连接（各自设超时/重试会失控）。
    """

    def __init__(self, timeout: int = 25, retries: int = 1, retry_wait: float = 4.0,
                 min_interval: float = 1.0):
        self.timeout = timeout
        self.retries = retries
        self.retry_wait = retry_wait
        self.min_interval = min_interval
        self._last = 0.0
        # ⭐ Cookie 罐：有的源需要"先访问首页拿 cookie 再调接口"（如雪球），
        #   全部走同一个 opener，cookie 自动透传，适配器不必自己拼 Cookie 头。
        self._jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self._jar))

    def _throttle(self):
        wait = self.min_interval - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)

    @staticmethod
    def _guard(url: str):
        """抓取前置合规检查：robots.txt（仅当 RESPECT_ROBOTS 打开时生效）。"""
        if RESPECT_ROBOTS and not robots_allows(url):
            raise RobotsDisallowed(url)

    @staticmethod
    def _classify(e: Exception, last: str) -> str:
        """把 429/403 识别出来抛 RateLimited（不重试）；其余返回原错误串继续重试。"""
        code = getattr(e, "code", None)
        if code in (429, 403):
            raise RateLimited(int(code))
        return last

    def get_text(self, url: str, headers: dict | None = None) -> str:
        """返回原始文本；失败抛异常（由 collect.py 记入 sources.last_err）。"""
        h = {"User-Agent": UA}
        if headers:
            h.update(headers)
        last = None
        for attempt in range(self.retries + 1):
            self._throttle()
            self._guard(url)
            try:
                req = urllib.request.Request(url, headers=h)
                with self._opener.open(req, timeout=self.timeout) as r:
                    return r.read().decode("utf-8", "replace")
            except Exception as e:  # noqa: BLE001 —— 统一记错，不区分类型
                last = self._classify(e, f"{type(e).__name__}: {str(e)[:90]}")
                if attempt < self.retries:
                    time.sleep(self.retry_wait)
            finally:
                self._last = time.time()
        raise RuntimeError(last or "request failed")

    def get_json(self, url: str, headers: dict | None = None):
        return json.loads(self.get_text(url, headers=headers))

    def get_bytes(self, url: str, headers: dict | None = None) -> bytes:
        """取原始字节（GBK 等非 UTF-8 站点需要，如吾爱破解的 GBK RSS）。"""
        h = {"User-Agent": UA}
        if headers:
            h.update(headers)
        last = None
        for attempt in range(self.retries + 1):
            self._throttle()
            self._guard(url)
            try:
                req = urllib.request.Request(url, headers=h)
                with self._opener.open(req, timeout=self.timeout) as r:
                    return r.read()
            except Exception as e:  # noqa: BLE001
                last = self._classify(e, f"{type(e).__name__}: {str(e)[:90]}")
                if attempt < self.retries:
                    time.sleep(self.retry_wait)
            finally:
                self._last = time.time()
        raise RuntimeError(last or "request failed")

    def post_json(self, url: str, body: dict | str | bytes | None = None,
                  headers: dict | None = None, form: bool = False):
        """POST 并发返回 JSON（36kr 等源需要）。

        form=True 时按 application/x-www-form-urlencoded 发送（NGA 那类要精确 Content-Length 的场景）。
        """
        if form and isinstance(body, dict):
            import urllib.parse as _up
            data = _up.urlencode(body).encode()
            ct = "application/x-www-form-urlencoded"
        elif isinstance(body, (bytes, bytearray)):
            data, ct = bytes(body), "application/octet-stream"
        elif isinstance(body, str):
            data, ct = body.encode("utf-8"), "application/json; charset=utf-8"
        else:
            data, ct = json.dumps(body or {}, ensure_ascii=False).encode("utf-8"), \
                "application/json; charset=utf-8"
        h = {"User-Agent": UA, "Content-Type": ct, "Content-Length": str(len(data))}
        if headers:
            h.update(headers)
        last = None
        for attempt in range(self.retries + 1):
            self._throttle()
            self._guard(url)
            try:
                req = urllib.request.Request(url, data=data, headers=h, method="POST")
                with self._opener.open(req, timeout=self.timeout) as r:
                    return json.loads(r.read().decode("utf-8", "replace"))
            except Exception as e:  # noqa: BLE001
                last = self._classify(e, f"{type(e).__name__}: {str(e)[:90]}")
                if attempt < self.retries:
                    time.sleep(self.retry_wait)
            finally:
                self._last = time.time()
        raise RuntimeError(last or "post failed")

    def get_text_curl(self, url: str, headers: dict | None = None) -> str:
        """用系统 `curl` 兜底获取（移植自 newsnow 的回退策略）。

        为什么需要：部分站点（如 FreeBuf）对 urllib 的 TLS/头部指纹直接下发
        **阿里云 WAF 挑战页**（HTTP 200 但内容是 html），而 curl 能正常拿到内容。
        适配器发现"内容形状不对"时可以调用本方法重试，而不是伪造数据。
        """
        cmd = ["curl", "-sL", "--max-time", str(self.timeout), "-A", UA,
               "--compressed", "-H", "Accept-Language: zh-CN,zh;q=0.9"]
        for k, v in (headers or {}).items():
            cmd += ["-H", f"{k}: {v}"]
        cmd.append(url)
        try:
            p = subprocess.run(cmd, capture_output=True, timeout=self.timeout + 10)
        except FileNotFoundError as e:
            raise RuntimeError("curl 不可用（镜像需安装 curl 才能启用 WAF 兜底）") from e
        if p.returncode != 0 or not p.stdout:
            raise RuntimeError(f"curl 回退失败 rc={p.returncode} err={p.stderr[:80]!r}")
        return p.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------- 适配器协议
@runtime_checkable
class Adapter(Protocol):
    """一个源适配器（模块级实现即可，见 adapters/__init__.py 的自动发现）。"""
    SRC_ID: str
    NAME: str
    CATEGORY: str

    def fetch(self, client: HttpClient) -> list[Item]:  # pragma: no cover - 协议
        ...


# ---------------------------------------------------------------- 旧引擎兼容层
def items_from_engine_payload(engine: str, payload: dict, cover_base: str = "") -> list[Item]:
    """把旧上游（dailyhot / newsnow）的响应形状转成 list[Item]。

    这段逻辑与 collect.py 历史上的 normalize() 完全等价（已搬移，行为不变），
    目的是让「外部引擎」与「自研源」共用同一个数据契约。
    """
    items: list[Item] = []
    # dailyhot: {"code":200,"name":"知乎","data":[{title,url,hot,...}]}
    if engine == "dailyhot" or ("data" in payload and isinstance(payload.get("data"), list)):
        for i, it in enumerate(payload.get("data") or [], 1):
            cover = it.get("cover")
            if cover and cover_base and not str(cover).startswith("http"):
                cover = cover_base.rstrip("/") + "/" + str(cover).lstrip("/")
            items.append(Item(
                ext_id=str(it.get("id") or it.get("url") or i),
                title=(it.get("title") or "").strip(),
                url=it.get("url") or it.get("mobileUrl"),
                rank=i,
                heat=num(it.get("hot") if it.get("hot") is not None
                         else it.get("heat") if it.get("heat") is not None
                         else it.get("num")),
                desc=it.get("desc"),
                cover=cover,
                author=it.get("author"),
                timestamp=it.get("timestamp") or None,
                extra={"engine": engine},
            ))
    # newsnow: {"status":"success","items":[{id,title,url,extra}]}
    elif "items" in payload:
        for i, it in enumerate(payload.get("items") or [], 1):
            extra = it.get("extra") if isinstance(it.get("extra"), dict) else {}
            items.append(Item(
                ext_id=str(it.get("id") or i),
                title=(it.get("title") or "").strip(),
                url=it.get("url") or extra.get("url"),
                rank=i,
                heat=num(extra.get("info")),
                desc=extra.get("desc") or extra.get("info"),
                cover=extra.get("icon"),
                author=extra.get("author"),
                timestamp=extra.get("date") if isinstance(extra.get("date"), int) else None,
                extra={"engine": engine, "raw_extra": extra} if extra else {"engine": engine},
            ))
    return [x for x in items if x.title]
