#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CSDN · 博客热榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/csdn.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://blog.csdn.net/phoenix/web/blog/hot-rank?page=0&pageSize=30（无鉴权）
响应：data[] → {productId,articleTitle,picList[],nickName,period,hotRankScore,articleDetailUrl}
热度：`hotRankScore`（热度分，字符串数字，实测 10⁴ 量级）→ **真热度**
"""
from __future__ import annotations

from .base import Item, num, ts_ms

SRC_ID = "csdn"
NAME = "CSDN热榜"
CATEGORY = "开发"

API = "https://blog.csdn.net/phoenix/web/blog/hot-rank?page=0&pageSize=30"
HEADERS = {"Referer": "https://blog.csdn.net/rank/list",
           # ⚠️ 实测：批量连采时 CSDN 会瞬时限流返回空 → 带浏览器 UA 明显更稳
           "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
           "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError("CSDN hot-rank 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("articleTitle") or "").strip()
        if not title:
            continue
        pics = x.get("picList") or []
        out.append(Item(
            ext_id=str(x.get("productId") or i),
            title=title,
            url=x.get("articleDetailUrl") or None,
            rank=i,
            heat=num(x.get("hotRankScore")),                # 热度分 = 真热度
            cover=pics[0] if pics else None,
            author=x.get("nickName") or None,
            timestamp=ts_ms(x.get("period")),               # "2026-10-19-11"
        ))
    return out
