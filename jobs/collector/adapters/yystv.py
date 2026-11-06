#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""游研社 · 首页文章

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/yystv.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.yystv.cn/home/get_home_docs_by_page（无鉴权）
响应：data[] → {id,title,cover,author,createtime}
热度：**无**（上游显式 undefined）→ heat=None
"""
from __future__ import annotations

from .base import Item, ts_ms

SRC_ID = "yystv"
NAME = "游研社"
CATEGORY = "娱乐"

API = "https://www.yystv.cn/home/get_home_docs_by_page"
HEADERS = {"Referer": "https://www.yystv.cn/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError("游研社 data 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        aid = x.get("id")
        if not (title and aid):
            continue
        out.append(Item(
            ext_id=str(aid),
            title=title,
            url=f"https://www.yystv.cn/p/{aid}",
            rank=i,
            heat=None,
            cover=x.get("cover") or None,
            author=x.get("author") or None,
            timestamp=ts_ms(x.get("createtime")),           # 形如 "2天前"
        ))
    return out
