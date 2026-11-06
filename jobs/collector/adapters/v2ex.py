#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""V2EX · 热门主题

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/v2ex.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.v2ex.com/api/topics/hot.json（type=latest 时换成 latest.json）
响应：顶层数组 → {id,title,content,url,replies,member.username}
热度：`replies`（回复数，通常 0~200）→ **真热度**
⚠️ 该接口常被限流/返空（实测本站点直连易空）→ 按规范抛明确异常，记入 sources.last_err
"""
from __future__ import annotations

from .base import Item, clip, num

SRC_ID = "v2ex"
NAME = "V2EX热门"
CATEGORY = "开发"

API = "https://www.v2ex.com/api/topics/hot.json"
HEADERS = {"Referer": "https://www.v2ex.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    rows = client.get_json(API, headers=HEADERS)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("V2EX 返回空（官方接口限流或已调整，需浏览器 UA/退化为页面解析）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        if not title:
            continue
        member = x.get("member") or {}
        out.append(Item(
            ext_id=str(x.get("id") or i),
            title=title,
            url=x.get("url") or (f"https://www.v2ex.com/t/{x.get('id')}" if x.get("id") else None),
            rank=i,
            heat=num(x.get("replies")),                     # 回复数 = 真热度
            desc=clip(x.get("content"), 300),
            author=member.get("username") if isinstance(member, dict) else None,
        ))
    return out
