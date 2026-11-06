#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知乎日报 · 今日推荐

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/zhihu-daily.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://daily.zhihu.com/api/4/news/latest
必需头：Referer + Host（上游这么写，照抄）
响应：{date, stories:[{id,title,images[],hint,url,type}]} → 只取 `type == 0` 的常规文章
热度：**无**；时间：**无**（上游两者都未提供）→ 只能按返回顺序排名
"""
from __future__ import annotations

from .base import Item

SRC_ID = "zhihu-daily"
NAME = "知乎日报"
CATEGORY = "综合"

API = "https://daily.zhihu.com/api/4/news/latest"
HEADERS = {"Referer": "https://daily.zhihu.com/api/4/news/latest", "Host": "daily.zhihu.com"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    stories = (payload or {}).get("stories") or []
    rows = [x for x in stories if x.get("type") == 0]
    if not rows:
        raise RuntimeError("知乎日报 stories 为空（改版或被拦）")

    out: list[Item] = []
    for x in rows:
        title = (x.get("title") or "").strip()
        if not title:
            continue
        imgs = x.get("images") or []
        out.append(Item(
            ext_id=str(x.get("id") or title[:40]),
            title=title,
            url=x.get("url") or (f"https://daily.zhihu.com/story/{x.get('id')}" if x.get("id") else None),
            rank=len(out) + 1,
            heat=None,
            cover=imgs[0] if imgs else None,
            author=x.get("hint") or None,
            extra={"date": payload.get("date")} if payload.get("date") else None,
        ))
    return out
