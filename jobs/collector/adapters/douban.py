#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 · 近期热门电影

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/douban.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://m.douban.com/rexxar/api/v2/subject/recent_hot/movie
⚠️ 实测：**缺 `Referer: https://movie.douban.com/` 会返回 400 invalid_request_1284**，必须带
规范第 4 条：豆瓣评分是"评分"不是"热度" → 放 extra，heat 保持 None
"""
from __future__ import annotations

from .base import Item, clip, num

SRC_ID = "douban"
NAME = "豆瓣热门电影"
CATEGORY = "娱乐"

API = "https://m.douban.com/rexxar/api/v2/subject/recent_hot/movie"
HEADERS = {
    "Referer": "https://movie.douban.com/",          # 必需，缺了直接 400
    "Accept": "application/json, text/plain, */*",
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise RuntimeError(f"豆瓣响应形状异常（可能被风控）：keys={list(payload)[:6] if isinstance(payload, dict) else type(payload)}")

    out: list[Item] = []
    for i, x in enumerate(payload["items"], 1):
        title = (x.get("title") or "").strip()
        if not title:
            continue
        sid = x.get("id")
        sub = clip(x.get("card_subtitle"), 120)
        rating = ((x.get("rating") or {}).get("value")) if isinstance(x.get("rating"), dict) else None
        out.append(Item(
            ext_id=str(sid or i),
            title=title,
            url=f"https://movie.douban.com/subject/{sid}" if sid else x.get("uri"),
            rank=i,
            heat=None,                                    # 评分≠热度（规范第 4 条）
            desc=sub,
            cover=((x.get("pic") or {}).get("normal") or (x.get("pic") or {}).get("large")
                   if isinstance(x.get("pic"), dict) else None),
            extra={"rating": rating} if rating else None,
        ))
    return out
