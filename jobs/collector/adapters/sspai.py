#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""少数派 · 热门文章

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/sspai.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://sspai.com/api/v1/article/tag/page/get?limit=40&tag={tag}
      tag 默认"热门文章"（可选：应用推荐 / 生活方式 / 效率技巧 / 少数派播客，需 URL 编码）
响应：{error, data:[{id,title,summary,banner,author:{nickname},released_time,like_count}]}
热度：`like_count`（点赞数，实测 0~数百）→ 站点口径热度
⚠️ banner 是**相对路径**（如 2026/4/23/article/xxx.png）→ 必须补 CDN 前缀
"""
from __future__ import annotations

import urllib.parse

from .base import Item, clip, num, ts_ms

SRC_ID = "sspai"
NAME = "少数派"
CATEGORY = "科技"

API = "https://sspai.com/api/v1/article/tag/page/get?limit=40&tag={tag}"
CDN = "https://cdn.sspai.com/"          # 相对头图前缀（引擎侧配置里也有同一份）
HEADERS = {"Referer": "https://sspai.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    url = API.format(tag=urllib.parse.quote("热门文章"))
    payload = client.get_json(url, headers=HEADERS)
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError("少数派 data 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        aid = x.get("id")
        if not (title and aid):
            continue
        banner = x.get("banner") or ""
        if banner and not banner.startswith("http"):
            banner = CDN.rstrip("/") + "/" + banner.lstrip("/")
        author = x.get("author") or {}
        out.append(Item(
            ext_id=str(aid),
            title=title,
            url=f"https://sspai.com/post/{aid}",
            rank=i,
            heat=num(x.get("like_count")),                  # 点赞数（站点口径）
            desc=clip(x.get("summary"), 300),
            cover=banner or None,
            author=author.get("nickname") if isinstance(author, dict) else None,
            timestamp=ts_ms(x.get("released_time")),
        ))
    return out
