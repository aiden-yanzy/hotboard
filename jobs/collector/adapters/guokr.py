#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""果壳 · 科学文章

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/guokr.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.guokr.com/beta/proxy/science_api/articles?limit=30
响应：顶层 JSON **数组**，每项 {id,title,summary,small_image,author.nickname,date_modified,...}
热度：上游虽带 `sort_score`，但 DailyHotApi 显式置 undefined → 本适配器 **heat=None**
      （规范第 4 条：宁可无热度，也不把不明口径的分数写进 snapshots.heat）
"""
from __future__ import annotations

from .base import Item, clip, ts_ms

SRC_ID = "guokr"
NAME = "果壳"
CATEGORY = "科技"

API = "https://www.guokr.com/beta/proxy/science_api/articles?limit=30"
HEADERS = {"Referer": "https://www.guokr.com/"}


def fetch(client):
    rows = client.get_json(API, headers=HEADERS)
    if isinstance(rows, dict):                       # 兼容包一层 data 的形态
        rows = rows.get("data") or rows.get("result") or []
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("果壳 articles 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        if not title:
            continue
        author = x.get("author") or {}
        out.append(Item(
            ext_id=str(x.get("id") or i),
            title=title,
            url=f"https://www.guokr.com/article/{x.get('id')}/" if x.get("id") else None,
            rank=i,
            heat=None,                                # 上游未给可用热度
            desc=clip(x.get("summary"), 300),
            cover=x.get("small_image") or None,
            author=author.get("nickname") if isinstance(author, dict) else None,
            timestamp=ts_ms(x.get("date_modified")),
        ))
    return out
