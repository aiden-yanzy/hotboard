#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""腾讯新闻 · 热点榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/qq-news.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://r.inews.qq.com/gw/event/hot_ranking_list?page_size=50
响应：idlist[0].newslist[] —— ⚠️ **首条是占位项（"用户最关注热点"），必须跳过**
热度：`hotEvent.hotScore`（热度分，万~十万级）→ **真热度**
"""
from __future__ import annotations

from .base import Item, clip, num, ts_ms

SRC_ID = "qq-news"
NAME = "腾讯新闻热点"
CATEGORY = "综合"

API = "https://r.inews.qq.com/gw/event/hot_ranking_list?page_size=50"
HEADERS = {"Referer": "https://news.qq.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    idlist = (payload or {}).get("idlist") or []
    rows = (idlist[0] or {}).get("newslist") if idlist else None
    if not rows:
        raise RuntimeError("腾讯新闻 newslist 为空（改版或被拦）")

    out: list[Item] = []
    rank = 0
    for x in rows[1:]:                                   # ⭐ 跳过首条占位项
        title = (x.get("title") or "").strip()
        nid = x.get("id")
        if not (title and nid):
            continue
        rank += 1
        ev = x.get("hotEvent") or {}
        out.append(Item(
            ext_id=str(nid),
            title=title,
            url=f"https://new.qq.com/rain/a/{nid}",
            rank=rank,
            heat=num(ev.get("hotScore")),                   # 热度分 = 真热度
            desc=clip(x.get("abstract"), 300),
            cover=x.get("miniProShareImage") or None,
            author=x.get("source") or None,
            timestamp=ts_ms(x.get("timestamp")),
        ))
    return out
