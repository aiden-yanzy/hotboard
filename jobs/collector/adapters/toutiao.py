#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""今日头条 · 热榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/toutiao.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc（无鉴权）
响应：`data` 即数组 → {ClusterIdStr,Title,Image.url,HotValue}
热度：`HotValue`（字符串数字，实测 2000 万量级）→ **真热度**
"""
from __future__ import annotations

from .base import Item, num

SRC_ID = "toutiao"
NAME = "今日头条热榜"
CATEGORY = "综合"

API = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
HEADERS = {"Referer": "https://www.toutiao.com/"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("今日头条热榜为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("Title") or "").strip()
        cid = x.get("ClusterIdStr")
        if not (title and cid):
            continue
        img = x.get("Image") or {}
        out.append(Item(
            ext_id=str(cid),
            title=title,
            url=f"https://www.toutiao.com/trending/{cid}/",
            rank=i,
            heat=num(x.get("HotValue")),                    # 热度值 = 真热度
            cover=(img.get("url") if isinstance(img, dict) else None) or None,
            # ⚠️ 上游把 19 位雪花 id 当时间戳传（结果无意义）——这里如实置 None，不照抄错误语义
            timestamp=None,
        ))
    return out
