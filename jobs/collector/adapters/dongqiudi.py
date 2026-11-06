#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""懂球帝 · 首页文章流

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/dongqiudi.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://api.dongqiudi.com/app/tabs/web/1.json（JSON，无分页）
字段：articles[] → id/title/share/url/created_at/thumb/category
⚠️ url 优先级：share > url > 兜底 https://www.dongqiudi.com/article/{id}
规范第 4 条：category 是分类不是热度 → heat=None
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .base import Item, clip

SRC_ID = "dongqiudi"
NAME = "懂球帝"
CATEGORY = "娱乐"

API = "https://api.dongqiudi.com/app/tabs/web/1.json"
HEADERS = {"Accept": "application/json, text/plain, */*", "Referer": "https://www.dongqiudi.com/"}


def _ts(s) -> int | None:
    """created_at 形如 '2026-10-19 11:20:00'（北京时间）或 ISO 串 → epoch 秒"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        v = int(s)
        return v // 1000 if v > 10 ** 11 else v          # 毫秒则转秒
    txt = str(s).strip().replace("T", " ").replace("Z", "")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(txt[:19], fmt)
                       .replace(tzinfo=timezone(timedelta(hours=8))).timestamp())
        except Exception:  # noqa: BLE001
            continue
    return None


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    articles = (payload or {}).get("articles")
    if not isinstance(articles, list) or not articles:
        raise RuntimeError("懂球帝响应结构异常或为空（改版或被拦）")

    out: list[Item] = []
    for i, k in enumerate(articles, 1):
        title = (k.get("title") or "").strip()
        if not title:
            continue
        aid = k.get("id")
        link = k.get("share") or k.get("url") or (f"https://www.dongqiudi.com/article/{aid}" if aid else None)
        out.append(Item(
            ext_id=str(aid or link or i),
            title=title,
            url=link,
            rank=i,
            heat=None,                                    # 规范第 4 条
            desc=clip(k.get("description") or k.get("summary"), 300),
            cover=k.get("thumb") or None,
            timestamp=_ts(k.get("created_at")),
            extra={"category": k.get("category")} if k.get("category") else None,
        ))
    return out
