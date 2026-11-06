#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""什么值得买 · 好价榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/smzdm.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://post.smzdm.com/rank/json_more/?unit={unit}
      unit: 1=今日热门（默认）/ 7=周热门 / 30=月热门
响应：{error_code, data:[{article_id,title,content,pic_url,nickname,collection_count,time_sort,jump_link}]}
热度：`collection_count`（收藏数，实测两位数~几百）→ 站点口径热度
⚠️ 实测：不带浏览器 UA / Referer 会被反爬拦成 HTML → 必须带
"""
from __future__ import annotations

from .base import Item, clip, num, ts_ms

SRC_ID = "smzdm"
NAME = "什么值得买"
CATEGORY = "购物"

API = "https://post.smzdm.com/rank/json_more/?unit=1"
HEADERS = {
    "Referer": "https://post.smzdm.com/top/",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError(f"什么值得买 data 为空（error_code={(payload or {}).get('error_code')}，可能被反爬）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        aid = x.get("article_id")
        if not (title and aid):
            continue
        out.append(Item(
            ext_id=str(aid),
            title=title,
            url=x.get("jump_link") or f"https://post.smzdm.com/p/{aid}/",
            rank=i,
            heat=num(x.get("collection_count")),            # 收藏数（站点口径）
            desc=clip(x.get("content"), 300),
            cover=x.get("pic_url") or None,
            author=x.get("nickname") or None,
            timestamp=ts_ms(x.get("time_sort")),
        ))
    return out
