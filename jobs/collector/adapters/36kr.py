#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""36氪 · 热榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/36kr.ts
本文件为 Python 重写，仅使用标准库。

端点：POST https://gateway.36kr.com/api/mis/nav/home/nav/rank/{type}   (type: hot/video/comment/collect)
请求体：{"partner_id":"wap","param":{"siteId":1,"platformId":2},"timestamp":<当前毫秒>}
响应：data.data.<listKey>[]（listKey 随 type 变化：hotRankList/videoList/remarkList/collectList）
热度：`templateMaterial.statCollect`（**收藏数**，实测几十）→ 站点权重口径，映射为 heat
      ⚠️ 热门程度更接近 statRead（阅读数，实测 4 万），但为与上游一致仍用 statCollect
"""
from __future__ import annotations

import time

from .base import Item, clip, num, ts_ms

SRC_ID = "36kr"
NAME = "36氪热榜"
CATEGORY = "科技"

API = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/{type}"
LIST_KEY = {"hot": "hotRankList", "video": "videoList",
            "comment": "remarkList", "collect": "collectList"}
HEADERS = {"Referer": "https://www.36kr.com/"}


def fetch(client):
    body = {"partner_id": "wap", "param": {"siteId": 1, "platformId": 2},
            "timestamp": int(time.time() * 1000)}
    payload = client.post_json(API.format(type="hot"), body, headers=HEADERS)

    data = (payload or {}).get("data") or {}
    rows = data.get(LIST_KEY["hot"]) or []
    if not rows:
        raise RuntimeError("36氪 hotRankList 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        tpl = x.get("templateMaterial") or {}
        title = (tpl.get("widgetTitle") or "").strip()
        iid = x.get("itemId")
        if not (title and iid):
            continue
        out.append(Item(
            ext_id=str(iid),
            title=title,
            url=f"https://www.36kr.com/p/{iid}",
            rank=i,
            heat=num(tpl.get("statCollect")),               # 收藏数（站点口径）
            cover=tpl.get("widgetImage") or None,
            author=tpl.get("authorName") or None,
            timestamp=ts_ms(x.get("publishTime")),
            extra={"read": num(tpl.get("statRead"))} if tpl.get("statRead") else None,
        ))
    return out
