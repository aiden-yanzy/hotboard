#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""豆瓣 · 电影排行榜（chart）

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/douban-movie.ts
本文件为 Python 重写，仅使用标准库（正则代替 cheerio）。

端点：GET https://movie.douban.com/chart/（HTML，301 跟随；移动端 UA 实测可用）
解析：`.article tr.item` 每行 → a[href] 含 /subject/(数字)/、`.rating_nums` 评分、
      img src 封面、`p.pl` 摘要（含"xx人评价"）
热度：⭐ `span.pl` 里的**评价人数**（实测千~万级）→ 用作 heat（站点口径）
标题：上游拼成 `【评分】片名`（保持一致，便于与历史数据对齐）
"""
from __future__ import annotations

import re

from .base import Item, clip, num

SRC_ID = "douban-movie"
NAME = "豆瓣电影榜"
CATEGORY = "娱乐"

URL = "https://movie.douban.com/chart/"
HEADERS = {
    "Referer": "https://movie.douban.com/",
    "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"),
}
_ROW = re.compile(r'<tr[^>]*class="[^"]*item[^"]*"[^>]*>(.*?)</tr>', re.S)
_HREF = re.compile(r'href="[^"]*?/subject/(\d+)/"', re.S)
_NAME = re.compile(r'<a[^>]+title="([^"]+)"', re.S)
_RATING = re.compile(r'<span[^>]*class="rating_nums"[^>]*>([^<]*)</span>', re.S)
_IMG = re.compile(r'<img[^>]+src="([^"]+)"', re.S)
_PL = re.compile(r'<p[^>]*class="pl"[^>]*>(.*?)</p>', re.S)


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    rows = _ROW.findall(html)
    if not rows:
        raise RuntimeError("豆瓣 chart 未匹配到 tr.item（改版或被拦）")

    out: list[Item] = []
    for row in rows:
        m_id, m_name = _HREF.search(row), _NAME.search(row)
        if not m_name:
            continue
        name = _txt(m_name.group(1))
        if not name:
            continue
        m_rating = _RATING.search(row)
        score = _txt(m_rating.group(1)) if m_rating else "0.0"
        m_pl, m_img = _PL.search(row), _IMG.search(row)
        pl = _txt(m_pl.group(1)) if m_pl else ""
        num_m = re.search(r"(\d+)人评价", pl)
        sid = m_id.group(1) if m_id else None
        out.append(Item(
            ext_id=str(sid or name[:40]),
            title=f"【{score}】{name}",
            url=f"https://movie.douban.com/subject/{sid}/" if sid else None,
            rank=len(out) + 1,
            heat=num(num_m.group(1)) if num_m else None,      # 评价人数（站点口径）
            desc=clip(pl, 300) or None,
            cover=m_img.group(1) if m_img else None,
        ))
    return out
