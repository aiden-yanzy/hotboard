#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""虎嗅 · 24小时

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/huxiu.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://moment-api.huxiu.com/web-v3/moment/feed?platform=www
响应：data.moment_list.datalist[] → {object_id, content(含<br>的 HTML), publish_time(秒),
      count_info:{agree_num,...}, user_info:{username}}
热度：⭐ `count_info.agree_num` 实测**恒为 0** → 按规范置 **heat=None**
      （不把 0 写进 snapshots.heat）
标题处理：把 <br> 换行后取第一个非空行当标题，其余作为 desc（与上游做法一致）
"""
from __future__ import annotations

import re

from .base import Item, clip, ts_ms

SRC_ID = "huxiu"
NAME = "虎嗅24小时"
CATEGORY = "科技"

API = "https://moment-api.huxiu.com/web-v3/moment/feed?platform=www"
HEADERS = {"Referer": "https://www.huxiu.com/moment/",
           "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (((payload or {}).get("data") or {}).get("moment_list") or {}).get("datalist") or []
    if not rows:
        raise RuntimeError("虎嗅 datalist 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        raw = re.sub(r"<br\s*/?>", "\n", x.get("content") or "")
        text = re.sub(r"<[^>]+>", "", raw)
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if not lines:
            continue
        title = lines[0].rstrip("。")
        oid = x.get("object_id")
        user = x.get("user_info") or {}
        out.append(Item(
            ext_id=str(oid or i),
            title=title[:120],
            url=f"https://www.huxiu.com/moment/{oid}.html" if oid else None,
            rank=i,
            heat=None,                                       # agree_num 恒 0 → 不给热度
            desc=clip(" ".join(lines[1:]), 300) if len(lines) > 1 else None,
            author=user.get("username") if isinstance(user, dict) else None,
            timestamp=ts_ms(x.get("publish_time")),
        ))
    return out
