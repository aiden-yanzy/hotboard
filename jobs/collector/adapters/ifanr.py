#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""爱范儿 · 快讯

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/ifanr.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://sso.ifanr.com/api/v5/wp/buzz/?limit=20&offset=0
响应：objects[] → {id,post_id,post_title,post_content(HTML),created_at(秒),like_count,comment_count,buzz_original_url}
热度：`like_count || comment_count` 实测**常为 0** → 按规范置 **heat=None**
封面：从 post_content 里取第一张 <img src>
"""
from __future__ import annotations

import re

from .base import Item, clip, num, ts_ms

SRC_ID = "ifanr"
NAME = "爱范儿快讯"
CATEGORY = "科技"

API = "https://sso.ifanr.com/api/v5/wp/buzz/?limit=20&offset=0"
HEADERS = {"Referer": "https://www.ifanr.com/", "Accept": "application/json, text/plain, */*"}
_IMG = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("objects") or []
    if not rows:
        raise RuntimeError("爱范儿 objects 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("post_title") or "").strip()
        bid = x.get("id")
        if not (title and bid):
            continue
        content = x.get("post_content") or ""
        m = _IMG.search(content)
        like = num(x.get("like_count")) or num(x.get("comment_count"))
        pid = x.get("post_id")
        out.append(Item(
            ext_id=str(bid),
            title=title,
            url=x.get("buzz_original_url") or (f"https://www.ifanr.com/{pid}" if pid else None),
            rank=i,
            heat=like if like else None,                     # 恒 0 → None
            desc=clip(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", content)), 300),
            cover=m.group(1) if m else None,
            timestamp=ts_ms(x.get("created_at")),
        ))
    return out
