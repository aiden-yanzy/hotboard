#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""51CTO · 推荐

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/51cto.ts
本文件为 Python 重写，仅使用标准库。

端点：① token: GET https://api-media.51cto.com/api/token-get → data.data.token
      ② 列表: GET https://api-media.51cto.com/index/index/recommend
              ?page=1&page_size=50&limit_time=0&name_en=&timestamp={ms}&token={token}&sign={sign}
签名（上游逐字）：
      sign = md5( md5(requestPath) + md5( 参数名升序逗号拼接 + md5(token) + timestamp ) )
      ⚠️ 实测服务端**目前不校验 sign**（乱填也返 200）→ 本适配器照抄算法，失败也不影响
响应：data.data.list[] → {title, abstract, cover, pubdate, url}
热度：**无**；id：上游读 source_id（响应里没有）→ 这里从 url 里提数字
"""
from __future__ import annotations

import hashlib
import re
import time

from .base import Item, clip, ts_ms

SRC_ID = "51cto"
NAME = "51CTO推荐"
CATEGORY = "开发"

TOKEN_API = "https://api-media.51cto.com/api/token-get"
PATH = "index/index/recommend"
LIST_API = ("https://api-media.51cto.com/" + PATH +
            "?page=1&page_size=50&limit_time=0&name_en=&timestamp={ts}&token={token}&sign={sign}")
HEADERS = {"Referer": "https://www.51cto.com/", "Accept": "application/json, text/plain, */*"}


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _sign(token: str, ts: int) -> str:
    keys = ",".join(sorted(["limit_time", "name_en", "page", "page_size", "timestamp", "token"]))
    inner = _md5(keys + _md5(token) + str(ts))
    return _md5(_md5(PATH) + inner)


def fetch(client):
    tok = client.get_json(TOKEN_API, headers=HEADERS)
    token = (((tok or {}).get("data") or {}).get("data") or {}).get("token")
    ts = int(time.time() * 1000)
    if token:
        url = LIST_API.format(ts=ts, token=token, sign=_sign(token, ts))
    else:                                     # 拿不到 token 也试一次（签名当前不校验）
        url = LIST_API.format(ts=ts, token="", sign="")
    payload = client.get_json(url, headers=HEADERS)

    d = (payload or {}).get("data") or {}
    rows = (d.get("data") or d).get("list") if isinstance(d, dict) else None
    if not rows:
        raise RuntimeError(f"51CTO list 为空（code={(payload or {}).get('code')}）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        if not title:
            continue
        u = x.get("url") or ""
        m = re.search(r"/(\d+)(?:\.html)?$", u)
        out.append(Item(
            ext_id=m.group(1) if m else (u or str(i)),
            title=title,
            url=u or None,
            rank=i,
            heat=None,
            desc=clip(x.get("abstract"), 300),
            cover=x.get("cover") or None,
            timestamp=ts_ms(x.get("pubdate")),
        ))
    return out
