#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中央气象台 · 预警

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/weatheralarm.ts
本文件为 Python 重写，仅使用标准库。

端点：GET http://www.nmc.cn/rest/findAlarm?pageNo=1&pageSize=20&signaltype=&signallevel=&province=
      ⚠️ 注意是 **http**（非 https）；province 中文需 URL 编码
响应：data.page.list[] → {alertid,title,issuetime,pic,url}
热度：**无** → heat=None；desc 用「发布时间 + 标题」（与上游一致）
"""
from __future__ import annotations

from .base import Item, clip, ts_ms

SRC_ID = "weatheralarm"
NAME = "气象预警"
CATEGORY = "综合"

API = "http://www.nmc.cn/rest/findAlarm?pageNo=1&pageSize=20&signaltype=&signallevel=&province="
HEADERS = {"Referer": "http://www.nmc.cn/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (((payload or {}).get("data") or {}).get("page") or {}).get("list") or []
    if not rows:
        raise RuntimeError("气象台 findAlarm 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        aid = x.get("alertid")
        if not (title and aid):
            continue
        issue = x.get("issuetime") or ""
        url = x.get("url") or ""
        out.append(Item(
            ext_id=str(aid),
            title=title,
            url=("http://nmc.cn" + url) if url.startswith("/") else (url or "http://www.nmc.cn/"),
            rank=i,
            heat=None,
            desc=clip(f"{issue} {title}".strip(), 300),
            cover=x.get("pic") or None,
            timestamp=ts_ms(issue),
        ))
    return out
