#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新浪新闻 · 排行榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/sina-news.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://top.{www}.sina.com.cn/ws/GetTopDataList.php
        ?top_type=day&top_cat={params}&top_time={YYYYMMDD}&top_show_num=50
      type=1（默认）对应 `news/www_www_all_suda_suda`
响应：JSONP 风格 `var data = {...};` → 去掉前后缀后解析；结构 data[] →
      {id,title,media,top_num,create_date,create_time,url}
热度：`top_num`（数字串，实测数百~数千）→ **真热度**
⚠️ top_time 用**当天日期**（跨零点要重取）
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from .base import Item, num, ts_ms

SRC_ID = "sina-news"
NAME = "新浪新闻榜"
CATEGORY = "综合"

CAT_MAP = {1: "www_www_all_suda_suda", 2: "video_news_all_by_vv",
           3: "total_slide_suda", 4: "news_china_suda",
           5: "news_world_suda", 6: "news_society_suda",
           7: "sports_suda", 8: "finance_0_suda",
           9: "ent_suda", 10: "tech_news_suda", 11: "news_mil_suda"}
# ⚠️ 实测：top_cat **不能**带 `news/` 前缀（带前缀只回 `{"conf":{...}}` 空壳），去掉才返回 50 条
API = ("https://top.news.sina.com.cn/ws/GetTopDataList.php"
       "?top_type=day&top_cat={cat}&top_time={day}&top_show_num=50")
HEADERS = {"Referer": "https://top.news.sina.com.cn/", "Accept": "*/*"}
_PREFIX = re.compile(r"^\s*var\s+data\s*=\s*")


def fetch(client):
    day = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d")   # 项目时区 +8
    raw = client.get_text(API.format(cat=CAT_MAP[1], day=day), headers=HEADERS)
    body = _PREFIX.sub("", raw.strip()).rstrip(";").strip()
    if not body.startswith(("{", "[")):
        raise RuntimeError("新浪新闻榜响应不是 JSONP 数据（改版或被拦）")
    import json as _json
    payload = _json.loads(body)
    rows = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("新浪新闻榜 data 为空")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        if not title:
            continue
        top_num = x.get("top_num")
        out.append(Item(
            ext_id=str(x.get("id") or i),
            title=title,
            url=x.get("url") or None,
            rank=i,
            heat=num(str(top_num).replace(",", "")) if top_num is not None else None,
            author=x.get("media") or None,
            timestamp=ts_ms(f"{x.get('create_date') or ''} {x.get('create_time') or ''}".strip()),
        ))
    return out
