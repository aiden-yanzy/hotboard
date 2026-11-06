#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""开源中国 OSCHINA · 资讯列表

来源：参照站 rebang.today 有此源（`oschina`）而我们没有 → 实测后自研。
⚠️ 自行实测写出（未使用 RSSHub 的 AGPL 代码）。

端点：GET https://www.oschina.net/news/widgets/_news_index_all_list?p=1&type=rss
      （资讯页的"列表 widget"接口，返回 HTML 片段，免鉴权）
解析：`<div class="item news-item">` → `<h3 class="header"><a href="URL" title="标题">`
热度：**无**（widget 里没有阅读/推荐数）→ heat=None
"""
from __future__ import annotations

import re

from .base import Item, clip

SRC_ID = "oschina"
NAME = "开源中国"
CATEGORY = "开发"

API = "https://www.oschina.net/news/widgets/_news_index_all_list?p=1&type=rss"
HEADERS = {"Referer": "https://www.oschina.net/news", "Accept": "text/html, */*"}
_ITEM = re.compile(
    r'<div class="item news-item">.*?<h3 class="header">\s*<a\s+href="([^"]+)"[^>]*title="([^"]*)"[^>]*>',
    re.S)
_DESC = re.compile(r'<div class="description">\s*<p[^>]*>(.*?)</p>', re.S)
_IMG = re.compile(r'<img[^>]+src="([^"]+)"', re.S)


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(API, headers=HEADERS)
    blocks = re.split(r'(?=<div class="item news-item">)', html)[1:]
    items = []
    for b in blocks:
        m = _ITEM.match(b)
        if not m:
            continue
        url, title = m.group(1).strip(), (m.group(2) or "").strip()
        if not title:
            h3 = re.search(r"<h3 class=\"header\">\s*<a[^>]*>(.*?)</a>", b, re.S)
            title = _txt(h3.group(1)) if h3 else ""
        if not (title and url):
            continue
        d = _DESC.search(b)
        img = _IMG.search(b)
        items.append((url, title, clip(_txt(d.group(1)), 300) if d else None,
                      img.group(1) if img else None))
    if not items:
        raise RuntimeError("开源中国 widget 未匹配到 news-item（改版或被拦）")

    out: list[Item] = []
    for i, (url, title, desc, cover) in enumerate(items[:30], 1):
        m = re.search(r"/news/(\d+)", url)
        out.append(Item(
            ext_id=m.group(1) if m else url,
            title=title,
            url=url if url.startswith("http") else f"https://www.oschina.net{url}",
            rank=i,
            heat=None,
            desc=desc,
            cover=cover,
        ))
    return out
