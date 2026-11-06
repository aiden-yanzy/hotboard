#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""抖音 · 热搜榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/douyin.ts
本文件为 Python 重写，仅使用标准库。

两步（照抄上游）：
  1. GET https://www.douyin.com/passport/general/login_guiding_strategy/?aid=6383
     从 set-cookie 里取 `passport_csrf_token`（HttpClient 的 Cookie 罐会自动带上）
  2. GET https://www.douyin.com/aweme/v1/web/hot/search/list/?device_platform=webapp&aid=6383
          &channel=channel_pc_web&detail_list=1
响应：data.word_list[] → {sentence_id,word,event_time,hot_value}
热度：`hot_value`（实测百万级）→ **真热度**
⚠️ 实测：抖音当前**不再下发** passport_csrf_token，且无有效 cookie 时返回空 body
   → 本适配器会如实抛错并记入 sources.last_err（不伪造数据）；要拿数据需真实浏览器 cookie
"""
from __future__ import annotations

from .base import Item, num, ts_ms

SRC_ID = "douyin"
NAME = "抖音热搜"
CATEGORY = "娱乐"

COOKIE_API = "https://www.douyin.com/passport/general/login_guiding_strategy/?aid=6383"
LIST_API = ("https://www.douyin.com/aweme/v1/web/hot/search/list/"
            "?device_platform=webapp&aid=6383&channel=channel_pc_web&detail_list=1")
HEADERS = {
    "Referer": "https://www.douyin.com/",
    "Accept": "application/json, text/plain, */*",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}


def fetch(client):
    try:
        client.get_text(COOKIE_API, headers=HEADERS)      # 暖场拿 cookie（罐内自动透传）
    except Exception:  # noqa: BLE001 —— 拿不到也继续试列表接口
        pass

    payload = client.get_json(LIST_API, headers=HEADERS)
    rows = ((payload or {}).get("data") or {}).get("word_list") or []
    if not rows:
        raise RuntimeError("抖音热搜返回空（缺少有效 cookie / 被风控，需真实浏览器凭据）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("word") or "").strip()
        sid = x.get("sentence_id")
        if not title:
            continue
        out.append(Item(
            ext_id=str(sid or i),
            title=title,
            url=f"https://www.douyin.com/hot/{sid}" if sid else None,
            rank=i,
            heat=num(x.get("hot_value")),                   # 热度值 = 真热度
            timestamp=ts_ms(x.get("event_time")),
        ))
    return out
