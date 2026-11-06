#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""英雄联盟 · 官方视频榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/lol.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://apps.game.qq.com/cmc/zmMcnTargetContentList
        ?r0=json&page=1&num=30&target=24&source=web_pc
响应：data.result[] → {iDocID,sTitle,sIMG,sAuthor,iTotalPlay,sCreated}
热度：`iTotalPlay`（播放量，实测 10⁰~10⁴ 分布极不均）→ **真热度**
⚠️ sIMG 是协议相对地址（`//static...`）→ 需补 `https:`
"""
from __future__ import annotations

import urllib.parse

from .base import Item, num, ts_ms

SRC_ID = "lol"
NAME = "英雄联盟视频"
CATEGORY = "娱乐"

API = ("https://apps.game.qq.com/cmc/zmMcnTargetContentList"
       "?r0=json&page=1&num=30&target=24&source=web_pc")
HEADERS = {"Referer": "https://lol.qq.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("result") or []
    if not rows:
        raise RuntimeError("英雄联盟 data.result 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("sTitle") or "").strip()
        docid = x.get("iDocID")
        if not (title and docid):
            continue
        img = x.get("sIMG") or ""
        if img.startswith("//"):
            img = "https:" + img
        out.append(Item(
            ext_id=str(docid),
            title=title,
            url="https://lol.qq.com/news/detail.shtml?docid=" + urllib.parse.quote(str(docid)),
            rank=i,
            heat=num(x.get("iTotalPlay")),                  # 播放量 = 真热度
            cover=img or None,
            author=x.get("sAuthor") or None,
            timestamp=ts_ms(x.get("sCreated")),
        ))
    return out
