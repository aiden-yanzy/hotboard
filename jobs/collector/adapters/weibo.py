#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微博 · 热搜榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/weibo.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://weibo.com/ajax/side/hotSearch
必需头：Referer: https://weibo.com/ + 桌面 Chrome UA
响应：data.realtime[] → {mid, word, word_scheme, num, onboard_time, ...}
热度：⭐ 这里**比上游多取一点**：DailyHotApi 显式置 hot=undefined，但响应里本就有
      `num`（热搜热度值，实测百万级）→ 本适配器采用 **num 作为 heat**（对产品是净收益，
      会让微博第一次有热度趋势）。若要与历史数据严格对齐，把 heat 改回 None 即可。
"""
from __future__ import annotations

import urllib.parse

from .base import Item, clip, num, ts_ms

SRC_ID = "weibo"
NAME = "微博热搜"
CATEGORY = "综合"

API = "https://weibo.com/ajax/side/hotSearch"
HEADERS = {
    "Referer": "https://weibo.com/",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("realtime") or []
    if not rows:
        raise RuntimeError("微博 realtime 为空（可能被风控，需要新鲜 cookie）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("word") or x.get("word_scheme") or "").strip()
        if not title:
            continue
        mid = x.get("mid") or x.get("word_scheme") or f"weibo-{i}"
        out.append(Item(
            ext_id=str(mid),
            title=title,
            url="https://s.weibo.com/weibo?q=" + urllib.parse.quote(f"#{title}#"),
            rank=i,
            heat=num(x.get("num")),                         # ⭐ 上游未用，本适配器启用
            desc=clip(x.get("word_scheme") or f"#{title}#", 120),
            timestamp=ts_ms(x.get("onboard_time")),
        ))
    return out
