#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""纽约时报 · RSS（中文站 / 全球）

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/nytimes.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://cn.nytimes.com/rss/            （type=china，默认）
      GET https://rss.nytimes.com/services/xml/rss/nyt/World.xml （type=global）
热度：**无** → heat=None
⚠️ 中文站需移动端 UA；本机沙盒对 nytimes 域名可能不可达（DNS/网络）
"""
from __future__ import annotations

from .base import Item, clip, parse_rss, strip_html, ts_ms

SRC_ID = "nytimes"
NAME = "纽约时报"
CATEGORY = "综合"

FEED = "https://cn.nytimes.com/rss/"
HEADERS = {
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "User-Agent": ("Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"),
}


def fetch(client):
    raw = client.get_text(FEED, headers=HEADERS)
    if "<rss" not in raw[:800] and "<feed" not in raw[:800]:
        raise RuntimeError("纽约时报 RSS 不可用（网络不可达或被拦）")
    rows = parse_rss(raw)
    if not rows:
        raise RuntimeError("纽约时报 RSS 解析为空")

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
