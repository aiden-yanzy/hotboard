#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度 · 热搜榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/baidu.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://top.baidu.com/board?tab=realtime（HTML，无鉴权）
解析：正则抓内嵌 JSON `<!--s-data:{...}-->` → data.cards[0].content[]
热度：`hotScore`（热度分，实测 790 万量级）→ **真热度**
⚠️ 必须带桌面 UA，否则拿到空壳页
"""
from __future__ import annotations

import json
import re
import urllib.parse

from .base import Item, clip, num

SRC_ID = "baidu"
NAME = "百度热搜"
CATEGORY = "综合"

URL = "https://top.baidu.com/board?tab=realtime"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}
_SDATA = re.compile(r"<!--s-data:(.*?)-->", re.S)


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    m = _SDATA.search(html)
    if not m:
        raise RuntimeError("百度页面未找到 s-data 内嵌 JSON（改版或被拦）")
    try:
        data = json.loads(m.group(1))
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"百度 s-data 解析失败：{type(e).__name__}") from e

    d = data.get("data") or {}
    cards = d.get("cards") or data.get("cards") or []
    rows = ((cards[0] or {}).get("content") if cards else None) or []
    if rows and isinstance(rows[0], dict) and isinstance(rows[0].get("content"), list):
        rows = rows[0]["content"]                                # 偶尔再包一层
    if not rows:
        raise RuntimeError("百度 cards[0].content 为空（形状已变）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("word") or x.get("title") or "").strip()
        if not title:
            continue
        img = x.get("img") or ""
        if isinstance(img, dict):
            img = (img.get("src") or "")
        raw_url = x.get("rawUrl") or x.get("url") or None
        out.append(Item(
            ext_id=str(x.get("index") or i),
            title=title,
            url=raw_url or ("https://www.baidu.com/s?wd=" + urllib.parse.quote(x.get("query") or title)),
            rank=i,
            heat=num(x.get("hotScore") if x.get("hotScore") is not None else x.get("hotTag")),
            desc=clip(x.get("desc"), 300),
            cover=img or None,
            author=x.get("show") or None,
        ))
    return out
