#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hacker News · 首页热帖

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/hackernews.ts
本文件为 Python 重写，仅使用标准库（正则代替 cheerio）。

端点：GET https://news.ycombinator.com/（首页 HTML）
解析：`.athing` 每行（含 id 属性）→ `.titleline a` 取标题与链接；分数取 `#score_{id}` 里的数字
热度：`score`（points，典型几十~上千）→ **真热度**
⚠️ 实测本机（中国大陆）直连超时 → 需要可达网络；实现本身简单
"""
from __future__ import annotations

import re

from .base import Item, num

SRC_ID = "hackernews"
NAME = "Hacker News"
CATEGORY = "开发"

URL = "https://news.ycombinator.com/"
HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")}
_ANCHOR = re.compile(r'<tr[^>]*class="[^"]*athing[^"]*"', re.S)
_ID = re.compile(r'id="(\d+)"')
_TITLE = re.compile(r'<span class="titleline"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
_SCORE = re.compile(r'<span[^>]*id="score_\d+"[^>]*>([^<]*)</span>')


def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    # ⚠️ HN 的分数在**下一行**（.subtext 行）里，不能只截到本行 </tr> →
    #    按 athing 行切段，每段一直延伸到下一个 athing 为止（含 subtext）
    chunks = [c for c in _ANCHOR.split(html) if _ID.search(c) and "titleline" in c]
    if not chunks:
        raise RuntimeError("HN 首页未匹配到 athing 行（改版或被拦）")

    out: list[Item] = []
    for i, chunk in enumerate(chunks, 1):
        m = _TITLE.search(chunk)
        if not m:
            continue
        url, title = m.group(1).strip(), _txt(m.group(2))
        if not title:
            continue
        idm = _ID.search(chunk)
        sm = _SCORE.search(chunk)
        out.append(Item(
            ext_id=str(idm.group(1) if idm else i),
            title=title,
            url=url or (f"https://news.ycombinator.com/item?id={idm.group(1)}" if idm else None),
            rank=i,
            heat=num(sm.group(1)) if sm else None,          # points = 真热度
        ))
    return out
