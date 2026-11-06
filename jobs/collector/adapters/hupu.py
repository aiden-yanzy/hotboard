#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""虎扑 · 步行街主干道

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/hupu.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://m.hupu.com/api/v2/bbs/topicThreads?topicId={type}&page=1
      type: 1=主干道（默认）/ 6=恋爱区 / 11=校园区 / 12=历史区 / 612=摄影区
响应：data.topicThreads[] → {tid,title,username,replies,recommendNum,url}
热度：`replies`（回复数，实测几十~几百）→ **真热度**
"""
from __future__ import annotations

from .base import Item, num

SRC_ID = "hupu"
NAME = "虎扑步行街"
CATEGORY = "社区"

API = "https://m.hupu.com/api/v2/bbs/topicThreads?topicId=1&page=1"
HEADERS = {"Referer": "https://m.hupu.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("topicThreads") or []
    if not rows:
        raise RuntimeError("虎扑 topicThreads 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        tid = x.get("tid")
        if not (title and tid):
            continue
        out.append(Item(
            ext_id=str(tid),
            title=title,
            url=f"https://bbs.hupu.com/{tid}.html",
            rank=i,
            heat=num(x.get("replies")),                    # 回复数 = 真热度
            author=x.get("username") or None,
            extra={"recommend": num(x.get("recommendNum"))} if x.get("recommendNum") else None,
        ))
    return out
