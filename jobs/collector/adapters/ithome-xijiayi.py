#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""IT之家 · 喜加一（免费领游戏）

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/ithome-xijiayi.ts
本文件为 Python 重写，仅使用标准库（正则代替 cheerio）。

端点：GET https://www.ithome.com/zt/xijiayi（HTML）
解析：`.newslist li` 每项 → a[href] / `.newsbody h2` 标题 / `.newsbody p` 摘要 /
      `img[data-original]` 封面 / `span.time`（内文是 JS 包装，用引号内日期）/ `.comment` 评论数
热度：`.comment` 的评论数（实测个位~十位）→ 站点口径热度
"""
from __future__ import annotations

import re

from .base import Item, clip, num, ts_ms

SRC_ID = "ithome-xijiayi"
NAME = "IT之家喜加一"
CATEGORY = "娱乐"

URL = "https://www.ithome.com/zt/xijiayi"
HEADERS = {"Referer": "https://www.ithome.com/",
           "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")}

_LI = re.compile(r"<li[^>]*>(.*?)</li>", re.S)
_HREF = re.compile(r'<a[^>]+href="([^"]+)"', re.S)
_H2 = re.compile(r"<h2[^>]*>(.*?)</h2>", re.S)
_P = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
_COVER = re.compile(r'img[^>]+data-original="([^"]+)"', re.S)
_TIME = re.compile(r"class=\"time\"[^>]*>.*?'([^']+)'", re.S)     # span.time 内是 JS 包装的日期
_COMMENT = re.compile(r'class="comment"[^>]*>(.*?)</span>', re.S)


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    blocks = [b for b in _LI.findall(html) if "newsbody" in b or "data-original" in b]
    if not blocks:
        raise RuntimeError("IT之家喜加一页面未匹配到条目（改版或被拦）")

    out: list[Item] = []
    for b in blocks:
        m_href, m_h2 = _HREF.search(b), _H2.search(b)
        if not (m_href and m_h2):
            continue
        title = _txt(m_h2.group(1))
        if not title:
            continue
        href = m_href.group(1)
        if href.startswith("//"):
            href = "https:" + href
        m_cov, m_p, m_time, m_c = _COVER.search(b), _P.search(b), _TIME.search(b), _COMMENT.search(b)
        m_num = re.search(r"/(\d+)\.htm", href)
        out.append(Item(
            ext_id=str(m_num.group(1)) if m_num else href,
            title=title,
            url=href,
            rank=len(out) + 1,
            heat=num(_txt(m_c.group(1))) if m_c else None,      # 评论数（站点口径）
            desc=clip(_txt(m_p.group(1)), 300) if m_p else None,
            cover=m_cov.group(1) if m_cov else None,
            timestamp=ts_ms(m_time.group(1)) if m_time else None,
        ))
    return out
