#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数字尾巴 · 资讯

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/dgtle.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://opser.api.dgtle.com/v2/news/index（无参数、无鉴权）
响应：items[] → {id,title,content,cover,from,membernum,created_at(秒),type}
热度：`membernum`（参与人数，实测数百）→ **真热度**
"""
from __future__ import annotations

from .base import Item, clip, num, ts_ms

SRC_ID = "dgtle"
NAME = "数字尾巴"
CATEGORY = "科技"

API = "https://opser.api.dgtle.com/v2/news/index"


def fetch(client):
    payload = client.get_json(API)
    rows = (payload or {}).get("items") or []
    if not rows:
        raise RuntimeError("数字尾巴 items 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or x.get("content") or "").strip()
        nid = x.get("id")
        if not (title and nid):
            continue
        out.append(Item(
            ext_id=str(nid),
            title=title[:120],
            url=f"https://www.dgtle.com/news-{nid}-{x.get('type') or 1}.html",
            rank=i,
            heat=num(x.get("membernum")),                   # 参与人数 = 真热度
            desc=clip(x.get("content"), 300),
            cover=x.get("cover") or None,
            author=x.get("from") or None,
            timestamp=ts_ms(x.get("created_at")),
        ))
    return out
