#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""网易新闻 · 热点流

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/netease-news.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://m.163.com/fe/api/hot/news/flow（Content-Type 是 text/plain，但 body 是 JSON）
响应：{code:200, data:{list:[{title,docid,imgsrc,source,ptime,publishTime,createTime}]}}
热度：**无**（上游显式 undefined）→ heat=None，只能按返回顺序排名
"""
from __future__ import annotations

from .base import Item, ts_ms

SRC_ID = "netease-news"
NAME = "网易新闻"
CATEGORY = "综合"

API = "https://m.163.com/fe/api/hot/news/flow"
HEADERS = {"Referer": "https://m.163.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("list") or []
    if not rows:
        raise RuntimeError("网易新闻 list 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        docid = x.get("docid")
        if not (title and docid):
            continue
        out.append(Item(
            ext_id=str(docid),
            title=title,
            url=f"https://www.163.com/dy/article/{docid}.html",
            rank=i,
            heat=None,
            cover=x.get("imgsrc") or None,
            author=x.get("source") or None,
            timestamp=ts_ms(x.get("ptime") or x.get("publishTime") or x.get("createTime")),
        ))
    return out
