#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""极客公园 · 首页文章

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/geekpark.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://mainssl.geekpark.net/api/v2 （纯 JSON，无参数、无鉴权）
响应：homepage_posts[].post → {id,title,abstract,cover_url,authors[].nickname,views,published_timestamp}
热度：`views`（阅读数，实测几十~几千）→ **真热度**，映射为 heat
"""
from __future__ import annotations

from .base import Item, clip, num, ts_ms

SRC_ID = "geekpark"
NAME = "极客公园"
CATEGORY = "科技"

API = "https://mainssl.geekpark.net/api/v2"


def fetch(client):
    payload = client.get_json(API)
    rows = (payload or {}).get("homepage_posts") or []
    if not rows:
        raise RuntimeError("极客公园 homepage_posts 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        p = x.get("post") or {}
        title = (p.get("title") or "").strip()
        if not title:
            continue
        authors = p.get("authors") or []
        out.append(Item(
            ext_id=str(p.get("id") or i),
            title=title,
            url=f"https://www.geekpark.net/news/{p.get('id')}" if p.get("id") else None,
            rank=i,
            heat=num(p.get("views")),                     # 阅读数 = 真热度
            desc=clip(p.get("abstract"), 300),
            cover=p.get("cover_url") or None,
            author=(authors[0] or {}).get("nickname") if authors else None,
            timestamp=ts_ms(p.get("published_timestamp")),
        ))
    return out
