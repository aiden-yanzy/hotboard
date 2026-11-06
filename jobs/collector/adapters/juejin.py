#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""稀土掘金 · 文章热榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/juejin.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://api.juejin.cn/content_api/v1/content/article_rank?category_id={type}&type=hot
      type 默认 1（综合）
响应：data[] → {content:{content_id,title}, author:{name}, content_counter:{view,like,hot_rank,...}}
热度：`content_counter.hot_rank`（热度分，实测 10³）→ **真热度**（注意 ≠ view）
⚠️ 上游头里声明了 br 编码，标准库解不了 → 这里**不发送** Accept-Encoding
"""
from __future__ import annotations

from .base import Item, num

SRC_ID = "juejin"
NAME = "掘金热榜"
CATEGORY = "开发"

API = "https://api.juejin.cn/content_api/v1/content/article_rank?category_id=1&type=hot"
HEADERS = {"Referer": "https://juejin.cn/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError(f"掘金热榜为空（err_no={(payload or {}).get('err_no')}）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        c = x.get("content") or {}
        title = (c.get("title") or "").strip()
        cid = c.get("content_id")
        if not (title and cid):
            continue
        counter = x.get("content_counter") or {}
        author = (x.get("author") or {}).get("name")
        out.append(Item(
            ext_id=str(cid),
            title=title,
            url=f"https://juejin.cn/post/{cid}",
            rank=i,
            heat=num(counter.get("hot_rank")),              # 热度分 = 真热度
            author=author or None,
            extra={"view": num(counter.get("view")), "like": num(counter.get("like"))}
            if counter.get("view") else None,
        ))
    return out
