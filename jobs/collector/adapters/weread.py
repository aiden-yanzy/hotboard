#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""微信读书 · 分类榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）
  apps/engine/src/routes/weread.ts + apps/engine/src/utils/getToken/weread.ts
本文件为 Python 重写，仅使用标准库（hashlib 代替 md5 包）。

端点：GET https://weread.qq.com/web/bookListInCategory/{type}?rank=1
      type: rising（默认）/ hot_search / newbook / general_novel_rising / all
响应：books[] → {bookInfo:{bookId,title,author,intro,cover,publishTime}, readingCount}
热度：`readingCount`（阅读数，实测千~万）→ **真热度**
⚠️ 详情链接需要 `getWereadID(bookId)` 的 MD5 变体变换（已逐行移植，见下）
"""
from __future__ import annotations

import hashlib

from .base import Item, clip, num, ts_ms

SRC_ID = "weread"
NAME = "微信读书"
CATEGORY = "综合"

API = "https://weread.qq.com/web/bookListInCategory/rising?rank=1"
HEADERS = {
    "Referer": "https://weread.qq.com/",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def get_weread_id(book_id: str) -> str:
    """移植 getWereadID()：把 bookId 变换成详情页所需的 id（逐行照抄，勿改逻辑）。"""
    s = _md5(book_id)
    sub = s[:3]
    if book_id.isdigit():
        parts = [format(int(chunk), "x") for chunk in
                 (book_id[i:i + 9] for i in range(0, len(book_id), 9))]
        tag, lst = "3", parts
    else:
        tag, lst = "4", ["".join(format(ord(ch), "x") for ch in book_id)]
    sub += tag + "2" + s[-2:]
    for idx, part in enumerate(lst):
        sub += format(len(part), "x").zfill(2) + part
        if idx != len(lst) - 1:
            sub += "g"
    if len(sub) < 20:
        sub += s[:20 - len(sub)]
    return sub + _md5(sub)[:3]


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("books") or []
    if not rows:
        raise RuntimeError("微信读书 books 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        bi = x.get("bookInfo") or {}
        title = (bi.get("title") or "").strip()
        bid = bi.get("bookId")
        if not (title and bid):
            continue
        cover = (bi.get("cover") or "").replace("s_", "t9_")
        out.append(Item(
            ext_id=str(bid),
            title=title,
            url=f"https://weread.qq.com/web/bookDetail/{get_weread_id(str(bid))}",
            rank=i,
            heat=num(x.get("readingCount")),                # 阅读数 = 真热度
            desc=clip(bi.get("intro"), 300),
            cover=cover or None,
            author=bi.get("author") or None,
            timestamp=ts_ms(bi.get("publishTime")),
        ))
    return out
