#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""澎湃新闻 · 热榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/thepaper.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar（无鉴权）
响应：data.hotNews[] → {contId,name,pic,praiseTimes,pubTimeLong}
热度：`praiseTimes`（点赞数，实测百级）→ 站点口径的有限热度，映射为 heat
"""
from __future__ import annotations

from .base import Item, num, ts_ms

SRC_ID = "thepaper"
NAME = "澎湃新闻"
CATEGORY = "综合"

API = "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"
HEADERS = {"Referer": "https://www.thepaper.cn/"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("hotNews") or []
    if not rows:
        raise RuntimeError("澎湃 hotNews 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("name") or "").strip()
        cid = x.get("contId")
        if not (title and cid):
            continue
        out.append(Item(
            ext_id=str(cid),
            title=title,
            url=f"https://www.thepaper.cn/newsDetail_forward_{cid}",
            rank=i,
            heat=num(x.get("praiseTimes")),                 # 点赞数（站点口径）
            cover=x.get("pic") or None,
            timestamp=ts_ms(x.get("pubTimeLong")),
        ))
    return out
