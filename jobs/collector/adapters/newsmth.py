#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""水木社区 · 全站热帖

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/newsmth.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://wap.newsmth.net/wap/api/hot/global（无鉴权）
响应：data.topics[] → {firstArticleId, article:{subject,body,account:{name},topicId}, board:{title}}
热度：**无**（上游显式 undefined）→ heat=None
⚠️ 上游取的 `article.postTime` 实测不存在（帖子级只有 topic.flushTime）→ 时间戳可能为空，如实置 None
"""
from __future__ import annotations

from .base import Item, clip, ts_ms

SRC_ID = "newsmth"
NAME = "水木热帖"
CATEGORY = "社区"

API = "https://wap.newsmth.net/wap/api/hot/global"
HEADERS = {"Referer": "https://wap.newsmth.net/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("topics") or []
    if not rows:
        raise RuntimeError("水木 topics 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        a = x.get("article") or {}
        title = (a.get("subject") or "").strip()
        if not title:
            continue
        board = (x.get("board") or {}).get("title") or ""
        topic_id = a.get("topicId")
        account = a.get("account") or {}
        out.append(Item(
            ext_id=str(a.get("firstArticleId") or x.get("firstArticleId") or topic_id or i),
            title=title,
            url=(f"https://wap.newsmth.net/article/{topic_id}?title={board}&from=home"
                 if topic_id else "https://wap.newsmth.net/"),
            rank=i,
            heat=None,
            desc=clip(a.get("body"), 300),
            author=account.get("name") if isinstance(account, dict) else None,
            timestamp=ts_ms(a.get("postTime") or x.get("flushTime")),
            extra={"board": board} if board else None,
        ))
    return out
