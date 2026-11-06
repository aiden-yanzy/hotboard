#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""机核 GCORES · 文章列表

来源：参照站 rebang.today 有此源（`gcores`）而我们没有 → 实测端点后自研。
⚠️ 自行实测写出（未使用 RSSHub 的 AGPL 代码）。

端点：GET https://www.gcores.com/gapi/v1/articles?page%5Blimit%5D=20&sort=-published-at
      （机核官方 gapi；`page[limit]` 必须 URL 编码成 `page%5Blimit%5D`，否则返回 HTTP 400）
响应：{data:[{id, attributes:{title, likes-count, comments-count, bookmarks-count, plays,
      published-at, cover/thumb, ...}}]}
热度：⭐ `likes-count`（点赞数，实测 0~几十）→ 真热度；**拿不到时回落到 comments-count**
URL：响应里**没有 url 字段** → 用 id 拼 `https://www.gcores.com/articles/{id}`
"""
from __future__ import annotations

import urllib.parse

from .base import Item, clip, num, ts_ms

SRC_ID = "gcores"
NAME = "机核"
CATEGORY = "娱乐"

API = "https://www.gcores.com/gapi/v1/articles?page%5Blimit%5D=20&sort=-published-at"
HEADERS = {"Referer": "https://www.gcores.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError("机核 gapi data 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        a = x.get("attributes") or {}
        title = (a.get("title") or "").strip()
        gid = x.get("id")
        if not (title and gid):
            continue
        likes = num(a.get("likes-count"))
        comments = num(a.get("comments-count"))
        out.append(Item(
            ext_id=str(gid),
            title=title,
            url=f"https://www.gcores.com/articles/{gid}",
            rank=i,
            heat=likes if likes else comments,              # 点赞优先，其次评论数
            desc=clip(a.get("desc") or a.get("summary"), 300),
            cover=a.get("cover") or a.get("thumb") or None,
            timestamp=ts_ms(a.get("published-at")),
            extra={"评论数": comments, "收藏数": num(a.get("bookmarks-count"))},
        ))
    return out
