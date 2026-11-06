#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT之家 · 热榜（移动版排行页）

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/ithome.ts
本文件为 Python 重写，仅使用标准库（正则代替 cheerio）。

端点：GET https://m.ithome.com/rankm/（HTML）
解析：每个 `div.placeholder[data-news-id]` 为一条；取内部 a 的 href、
      `img[data-original]` 封面、`.plc-title` 标题、`.post-time` 时间、`.review-num` 评论数
热度：`.review-num` 的**评论数**（实测百级）→ 站点口径热度（非严格热度）
⚠️ 页面上有多个 tab（day-rank/week-rank…）混排 → 按 news-id 去重
"""
from __future__ import annotations

import re

from .base import Item, num, ts_ms

SRC_ID = "ithome"
NAME = "IT之家热榜"
CATEGORY = "科技"

URL = "https://m.ithome.com/rankm/"
HEADERS = {"Referer": "https://m.ithome.com/",
           "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                          "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1")}

_ANCHOR = re.compile(r'<div[^>]*data-news-id="(\d+)"', re.S)
_HREF = re.compile(r'<a[^>]+href="(https?://[^"]*?/(?:html|live)/(\d+)\.htm)"', re.S)
_TITLE = re.compile(r'class="plc-title"[^>]*>(.*?)</p>', re.S)
_COVER = re.compile(r'img[^>]+data-original="([^"]+)"', re.S)
_TIME = re.compile(r'class="post-time"[^>]*>(.*?)</p>', re.S)
_REVIEW = re.compile(r'class="review-num"[^>]*>(.*?)</span>', re.S)


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    chunks = [c for c in _ANCHOR.split(html)[1:] if "<a" in c]
    if not chunks:
        raise RuntimeError("IT之家排行页未匹配到 data-news-id（改版或被拦）")

    seen: set[str] = set()
    out: list[Item] = []
    for chunk in chunks:
        idm = _ANCHOR.search(chunk) or None
        news_id = None
        m_href = _HREF.search(chunk)
        href = m_href.group(1) if m_href else None
        news_id = m_href.group(2) if m_href else None
        if not news_id:
            continue
        if news_id in seen:                                  # 多 tab 去重
            continue
        m_title = _TITLE.search(chunk)
        title = _txt(m_title.group(1)) if m_title else ""
        if not title:
            continue
        seen.add(news_id)
        m_cov = _COVER.search(chunk)
        m_time = _TIME.search(chunk)
        m_rev = _REVIEW.search(chunk)
        out.append(Item(
            ext_id=str(news_id),
            title=title,
            url=href,
            rank=len(out) + 1,
            heat=num(_txt(m_rev.group(1))) if m_rev else None,   # 评论数（站点口径）
            cover=m_cov.group(1) if m_cov else None,
            timestamp=ts_ms(_txt(m_time.group(1))) if m_time else None,
            extra={"id": idm.group(1) if idm else None},
        ))
    return out
