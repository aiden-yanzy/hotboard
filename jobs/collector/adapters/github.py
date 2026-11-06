#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GitHub · Trending

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/github.ts
本文件为 Python 重写，仅使用标准库（正则代替 cheerio）。

端点：GET https://github.com/trending?since={type}   type: daily/weekly/monthly
解析：`article.Box-row` 每行 → h2 a 的 href（owner/repo）与文本、p.col-9 描述、
      `[itemprop=programmingLanguage]` 语言、`/stargazers` 链接文本（stars）
热度：`stars`（总 star 数，实测数千~几十万）→ **真热度**
⚠️ GitHub 反爬/结构变动需容错 → 行数解析为 0 时抛错
"""
from __future__ import annotations

import re

from .base import Item, clip, num

SRC_ID = "github"
NAME = "GitHub Trending"
CATEGORY = "开发"

URL = "https://github.com/trending?since=daily"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}
_ROW = re.compile(r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>(.*?)</article>', re.S)
_H2A = re.compile(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_DESC = re.compile(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>(.*?)</p>', re.S)
_LANG = re.compile(r'itemprop="programmingLanguage"[^>]*>(.*?)<', re.S)
_STARS = re.compile(r'/stargazers"[^>]*>(.*?)</a>', re.S)


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    rows = _ROW.findall(html)
    if not rows:
        raise RuntimeError("GitHub trending 未匹配到 article.Box-row（改版或被拦）")

    out: list[Item] = []
    for i, row in enumerate(rows, 1):
        m = _H2A.search(row)
        if not m:
            continue
        href = m.group(1).strip()
        repo = _txt(m.group(2)).replace(" ", "")
        if not repo:
            continue
        m_desc = _DESC.search(row)
        m_lang = _LANG.search(row)
        m_star = _STARS.search(row)
        desc = _txt(m_desc.group(1)) if m_desc else ""
        lang = _txt(m_lang.group(1)) if m_lang else ""
        stars = num(_txt(m_star.group(1)).replace(",", "")) if m_star else None
        out.append(Item(
            ext_id=href or str(i),
            title=repo,
            url=f"https://github.com{href}" if href.startswith("/") else href,
            rank=i,
            heat=stars,                                     # star 数 = 真热度
            desc=clip(desc, 300),
            extra={"language": lang} if lang else None,
        ))
    return out
