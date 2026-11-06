#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知乎 · 热榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/zhihu.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://api.zhihu.com/topstory/hot-lists/total?limit=50
响应：data[] → {target:{id,title,excerpt,url,created}, children:[{thumbnail}], detail_text}
热度：`detail_text` 形如 "2198 万热度" → parseFloat × 10000 = **真热度**（约 2000 万）
⚠️ children 可能为空数组 → 取封面必须防空；无 cookie 时可能 403/空（按规范抛错）
"""
from __future__ import annotations

import re

from .base import Item, clip, num, ts_ms

SRC_ID = "zhihu"
NAME = "知乎热榜"
CATEGORY = "综合"

API = "https://api.zhihu.com/topstory/hot-lists/total?limit=50"
HEADERS = {"Referer": "https://www.zhihu.com/hot",
           "Accept": "application/json, text/plain, */*"}


def _heat(detail_text) -> int | None:
    """'2198 万热度' → 21980000"""
    if not detail_text:
        return None
    m = re.match(r"^\s*([\d.]+)\s*(万|亿)?", str(detail_text))
    if not m:
        return None
    v = float(m.group(1))
    v *= {"万": 1e4, "亿": 1e8}.get(m.group(2) or "", 1)
    out = int(v)
    return out if out else None


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError("知乎热榜为空（可能需要 cookie 或被风控）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        t = x.get("target") or {}
        title = (t.get("title") or "").strip()
        if not title:
            continue
        children = x.get("children") or []
        cover = None
        if children and isinstance(children[0], dict):
            cover = children[0].get("thumbnail")
        qid = (t.get("url") or "").rstrip("/").split("/")[-1]
        out.append(Item(
            ext_id=str(t.get("id") or qid or i),
            title=title,
            url=f"https://www.zhihu.com/question/{qid}" if qid else t.get("url"),
            rank=i,
            heat=_heat(x.get("detail_text")),               # 万热度 → 真热度
            desc=clip(t.get("excerpt"), 300),
            cover=cover or None,
            timestamp=ts_ms(t.get("created")),
        ))
    return out
