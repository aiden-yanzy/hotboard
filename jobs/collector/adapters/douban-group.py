#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 · 小组讨论

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/douban-group.ts
本文件为 Python 重写，仅使用标准库（正则代替 cheerio）。

端点：GET https://www.douban.com/group/explore（302 跟随）
⚠️ **必须用桌面版 UA**：实测移动 UA 只拿到 12KB 精简页（.channel-item 数=0），
   桌面 UA 拿到 51KB（30 条）
热度：上游硬编码 0 → 本适配器按规范置 **heat=None**
时间：`span.pubtime` 是中文相对时间（"20分钟前"/"刚刚"）→ ts_ms 能解析前者，"刚刚"返回 None
"""
from __future__ import annotations

import re

from .base import Item, clip, ts_ms

SRC_ID = "douban-group"
NAME = "豆瓣小组"
CATEGORY = "社区"

URL = "https://www.douban.com/group/explore"
HEADERS = {
    "Referer": "https://www.douban.com/group/",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}
_ANCHOR = re.compile(r'<div[^>]*class="[^"]*channel-item[^"]*"', re.S)
_H3A = re.compile(r'<h3[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_IMG = re.compile(r'<div[^>]*class="[^"]*pic-wrap[^"]*"[^>]*>.*?<img[^>]+src="([^"]+)"', re.S)
_P = re.compile(r'<div[^>]*class="[^"]*block[^"]*"[^>]*>.*?<p[^>]*>(.*?)</p>', re.S)
_PUB = re.compile(r'<span[^>]*class="[^"]*pubtime[^"]*"[^>]*>(.*?)</span>', re.S)


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    chunks = [c for c in _ANCHOR.split(html)[1:] if "<h3" in c]
    if not chunks:
        raise RuntimeError("豆瓣小组未匹配到 channel-item（多为 UA 不对或触发登录墙）")

    out: list[Item] = []
    for c in chunks:
        m = _H3A.search(c)
        if not m:
            continue
        href, title = m.group(1), _txt(m.group(2))
        if not title:
            continue
        tid = re.search(r"/topic/(\d+)", href)
        m_img, m_p, m_pub = _IMG.search(c), _P.search(c), _PUB.search(c)
        out.append(Item(
            ext_id=tid.group(1) if tid else href,
            title=title,
            url=href if href.startswith("http") else f"https://www.douban.com{href}",
            rank=len(out) + 1,
            heat=None,
            desc=clip(_txt(m_p.group(1)), 300) if m_p else None,
            cover=m_img.group(1) if m_img else None,
            timestamp=ts_ms(_txt(m_pub.group(1))) if m_pub else None,
        ))
    return out
