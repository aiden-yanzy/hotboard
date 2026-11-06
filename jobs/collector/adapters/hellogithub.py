#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HelloGitHub · 精选

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/hellogithub.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://abroad.hellogithub.com/v1/?sort_by={sort}&tid=&page=1
      sort: featured=精选（默认）/ all=全部
响应：data[] → {item_id,title,summary,author,updated_at,clicks_total}
热度：`clicks_total`（点击数，实测数千）→ **真热度**
"""
from __future__ import annotations

from .base import Item, clip, num, ts_ms

SRC_ID = "hellogithub"
NAME = "HelloGitHub"
CATEGORY = "开发"

API = "https://abroad.hellogithub.com/v1/?sort_by=featured&tid=&page=1"


def fetch(client):
    payload = client.get_json(API)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError("HelloGitHub data 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        if not title:
            continue
        iid = x.get("item_id")
        out.append(Item(
            ext_id=str(iid or i),
            title=title,
            url=f"https://hellogithub.com/repository/{iid}" if iid else None,
            rank=i,
            heat=num(x.get("clicks_total")),               # 点击数 = 真热度
            desc=clip(x.get("summary"), 300),
            author=x.get("author") or None,
            timestamp=ts_ms(x.get("updated_at")),
        ))
    return out
