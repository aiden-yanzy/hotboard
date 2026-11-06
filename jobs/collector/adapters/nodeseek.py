#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NodeSeek · 最新主题（RSS）

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/nodeseek.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://rss.nodeseek.com/（RSS/Atom，无鉴权、无特殊头）
热度：**无** → heat=None
⚠️ 实测本机网络对 rss.nodeseek.com 的 DNS 解析被污染（TCP 超时）→ 需要可达网络；
   实现本身是标准 RSS 解析
"""
from __future__ import annotations

from .base import Item, clip, parse_rss, strip_html, ts_ms

SRC_ID = "nodeseek"
NAME = "NodeSeek"
CATEGORY = "社区"

FEED = "https://rss.nodeseek.com/"
HEADERS = {"Accept": "application/rss+xml, application/xml, text/xml, */*"}


def fetch(client):
    raw = client.get_text(FEED, headers=HEADERS)
    if "<rss" not in raw[:800] and "<feed" not in raw[:800]:
        raise RuntimeError("NodeSeek 响应不是 RSS（网络不可达或被拦）")
    rows = parse_rss(raw)
    if not rows:
        raise RuntimeError("NodeSeek RSS 解析为空")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        if not x["title"]:
            continue
        out.append(Item(
            ext_id=x["guid"] or x["link"] or str(i),
            title=x["title"],
            url=x["link"] or None,
            rank=len(out) + 1,
            heat=None,
            desc=clip(strip_html(x["desc"]), 300),
            cover=x["cover"],
            author=x["author"] or None,
            timestamp=ts_ms(x["pub"]),
        ))
    return out
