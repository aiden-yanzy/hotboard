#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""量子位 · 最新文章（WordPress REST API）

来源：参照站 rebang.today 有此源（`qbitai`）而我们没有 → 实测后自研。
⚠️ 自行实测写出（未使用 RSSHub 的 AGPL 代码）。

端点：GET https://www.qbitai.com/wp-json/wp/v2/posts?per_page=20&_fields=id,link,title,date,excerpt
      （站点是 WordPress → 官方 REST API，稳定且免鉴权）
响应：[{id, link, title:{rendered}, date, excerpt:{rendered}}]
热度：**无**（WP 不暴露阅读量）→ heat=None（宁缺勿造）
"""
from __future__ import annotations

from .base import Item, clip, ts_ms

SRC_ID = "qbitai"
NAME = "量子位"
CATEGORY = "科技"

API = ("https://www.qbitai.com/wp-json/wp/v2/posts"
       "?per_page=20&_fields=id,link,title,date,excerpt")
HEADERS = {"Referer": "https://www.qbitai.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = payload if isinstance(payload, list) else []
    if not rows:
        raise RuntimeError("量子位 wp-json 返回空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = ((x.get("title") or {}).get("rendered") or "").strip()
        if not title:
            continue
        ex = (x.get("excerpt") or {}).get("rendered") or ""
        out.append(Item(
            ext_id=str(x.get("id") or i),
            title=title,
            url=x.get("link") or None,
            rank=i,
            heat=None,
            desc=clip(ex, 300),
            timestamp=ts_ms(x.get("date")),
        ))
    return out
