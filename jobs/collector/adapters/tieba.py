#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度贴吧 · 热议榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/tieba.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://tieba.baidu.com/hottopic/browse/topicList（无鉴权）
响应：data.bang_topic.topic_list[] → {topic_id,topic_name,topic_desc,topic_pic,discuss_num,create_time,topic_url}
热度：`discuss_num`（讨论数，实测百万级）→ **真热度**
⚠️ topic_url 内含 HTML 实体 `&amp;` → 必须 html.unescape 还原
"""
from __future__ import annotations

import html

from .base import Item, clip, num, ts_ms

SRC_ID = "tieba"
NAME = "贴吧热议榜"
CATEGORY = "社区"

API = "https://tieba.baidu.com/hottopic/browse/topicList"
HEADERS = {"Referer": "https://tieba.baidu.com/"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (((payload or {}).get("data") or {}).get("bang_topic") or {}).get("topic_list") or []
    if not rows:
        raise RuntimeError("贴吧 topic_list 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("topic_name") or "").strip()
        tid = x.get("topic_id")
        if not (title and tid):
            continue
        url = html.unescape(x.get("topic_url") or "") or f"https://tieba.baidu.com/hottopic/browse/hottopic?topic_id={tid}"
        out.append(Item(
            ext_id=str(tid),
            title=title,
            url=url,
            rank=i,
            heat=num(x.get("discuss_num")),                 # 讨论数 = 真热度
            desc=clip(x.get("topic_desc"), 300),
            cover=x.get("topic_pic") or None,
            timestamp=ts_ms(x.get("create_time")),
        ))
    return out
