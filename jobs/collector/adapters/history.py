#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""百度百科 · 历史上的今天

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/history.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://baike.baidu.com/cms/home/eventsOnHistory/{MM}.json?_={ms}
      按"月"一个静态文件（MM 两位补零），`_` 为毫秒时间戳防缓存
响应：{"<MM>": {"<MMDD>": [ {year,title,festival,link,desc,cover,pic_share} ]}}
热度：**无** → heat=None（规范第 4 条：宁缺勿造）
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from .base import Item, clip, strip_html

SRC_ID = "history"
NAME = "历史上的今天"
CATEGORY = "综合"

API = "https://baike.baidu.com/cms/home/eventsOnHistory/{mm}.json?_={ms}"


def fetch(client):
    now = datetime.now(timezone(timedelta(hours=8)))       # 项目时区规范 +8
    mm = f"{now.month:02d}"
    mdd = f"{now.month:02d}{now.day:02d}"
    payload = client.get_json(API.format(mm=mm, ms=int(time.time() * 1000)))
    if not isinstance(payload, dict):
        raise RuntimeError("历史上的今天响应不是 JSON（改版或被拦）")

    day = (payload.get(mm) or {}).get(mdd) or []
    if not day:
        raise RuntimeError(f"历史上的今天 {mdd} 无数据（形状可能已变）")

    out: list[Item] = []
    for i, x in enumerate(day, 1):
        title = strip_html(x.get("title")) or ""
        if not title:
            continue
        out.append(Item(
            ext_id=str(x.get("link") or i),
            title=title,
            url=x.get("link") or None,
            rank=i,
            heat=None,                                     # 该源没有热度字段
            desc=clip(strip_html(x.get("desc")), 300),
            cover=(x.get("pic_share") if x.get("cover") else None) or None,
            extra={"year": x.get("year")} if x.get("year") else None,
        ))
    return out
