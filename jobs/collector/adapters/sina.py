#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新浪 · 热榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/sina.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://newsapp.sina.cn/api/hotlist?newsId=HB-1-snhs%2Ftop_news_list-{type}
      type 默认 all（可选 hotcmnt/minivideo/ent/ai/auto/mother/fashion/travel/esg）
响应：data.data.hotList[] → {base:{base:{uniqueId,url}}, info:{title,hotValue}}
热度：`info.hotValue` 是**中文单位串**（如 "1.2亿"/"3456万"）→ `cn_num()` 解析 → **真热度**
"""
from __future__ import annotations

from .base import Item, cn_num

SRC_ID = "sina"
NAME = "新浪热榜"
CATEGORY = "综合"

API = "https://newsapp.sina.cn/api/hotlist?newsId=HB-1-snhs%2Ftop_news_list-all"
HEADERS = {"Referer": "https://newsapp.sina.cn/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("hotList") or []
    if not rows:
        raise RuntimeError("新浪热榜 hotList 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        info = x.get("info") or {}
        base = ((x.get("base") or {}).get("base") or {})
        title = (info.get("title") or "").strip()
        if not title:
            continue
        out.append(Item(
            ext_id=str(base.get("uniqueId") or i),
            title=title,
            url=base.get("url") or None,
            rank=i,
            heat=cn_num(info.get("hotValue")),              # 中文单位 → 真热度
        ))
    return out
