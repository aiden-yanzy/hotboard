#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""吾爱破解 · 精选（RSS，GBK 编码）

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/52pojie.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.52pojie.cn/forum.php?mod=guide&view={view}&rss=1
      view: digest=精选（默认）/ hot / new / newthread
      ⚠️ 必须带移动端 Chrome UA，否则可能被拦
响应：**GBK 编码**的 RSS 2.0 → 先 decode('gbk') 再解析
热度：**无** → heat=None；该 feed 无 <guid> → id 回退为下标
"""
from __future__ import annotations

from .base import Item, clip, parse_rss, strip_html, ts_ms

SRC_ID = "52pojie"
NAME = "吾爱破解精选"
CATEGORY = "社区"

API = "https://www.52pojie.cn/forum.php?mod=guide&view=digest&rss=1"
HEADERS = {
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "User-Agent": ("Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36"),
}


def fetch(client):
    raw = client.get_bytes(API, headers=HEADERS).decode("gbk", "replace")
    if "<rss" not in raw[:800] and "<feed" not in raw[:800]:
        raise RuntimeError("吾爱破解响应不是 RSS（可能被 WAF/登录墙拦住）")
    rows = parse_rss(raw)
    if not rows:
        raise RuntimeError("吾爱破解 RSS 解析为空")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        if not x["title"]:
            continue
        out.append(Item(
            ext_id=x["guid"] or str(i),
            title=x["title"],
            url=x["link"] or None,
            rank=len(out) + 1,
            heat=None,
            desc=clip(strip_html(x["desc"]), 300),
            cover=x["cover"],
            author=x["author"] or None,
            timestamp=ts_ms(x["pub"]),                       # RFC822
        ))
    return out
