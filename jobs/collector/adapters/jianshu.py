#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简书 · 首页推荐

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/jianshu.ts
本文件为 Python 重写，仅使用标准库（正则代替 cheerio）。

端点：GET https://www.jianshu.com/（HTML）
解析：`ul.note-list li` 每项 → `a.title[href="/p/xxx"]` 标题与链接、`p.abstract` 摘要、`a.nickname` 作者
热度：**无**；时间：**无**（上游两者都显式 undefined）
⚠️ 简书有反爬，可能返回 403/壳页 → 解析为空即抛错
"""
from __future__ import annotations

import re

from .base import Item, clip

SRC_ID = "jianshu"
NAME = "简书"
CATEGORY = "社区"

URL = "https://www.jianshu.com/"
HEADERS = {"Referer": "https://www.jianshu.com",
           "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")}

_LI = re.compile(r"<li[^>]*data-note-id[^>]*>(.*?)</li>", re.S)
_TITLE = re.compile(r'<a[^>]+class="title"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_ABS = re.compile(r'<p[^>]*class="abstract"[^>]*>(.*?)</p>', re.S)
_NICK = re.compile(r'<a[^>]+class="nickname"[^>]*>(.*?)</a>', re.S)
_IMG = re.compile(r'<img[^>]+src="([^"]+)"', re.S)


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    blocks = _LI.findall(html)
    if not blocks:
        raise RuntimeError("简书首页未匹配到 note-list 条目（改版或被反爬）")

    out: list[Item] = []
    for b in blocks:
        m = _TITLE.search(b)
        if not m:
            continue
        href, title = m.group(1), _txt(m.group(2))
        if not title:
            continue
        m_abs, m_nick, m_img = _ABS.search(b), _NICK.search(b), _IMG.search(b)
        out.append(Item(
            ext_id=href.rstrip("/").split("/")[-1] or href,
            title=title,
            url=f"https://www.jianshu.com{href}" if href.startswith("/") else href,
            rank=len(out) + 1,
            heat=None,
            desc=clip(_txt(m_abs.group(1)), 300) if m_abs else None,
            cover=m_img.group(1) if m_img else None,
            author=_txt(m_nick.group(1)) if m_nick else None,
        ))
    return out
