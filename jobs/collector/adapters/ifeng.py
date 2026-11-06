#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""凤凰网 · 首页热点

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/ifeng.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.ifeng.com/（HTML）→ 页面内联 `var allData = {...};`
      取 allData.hotNews1（{url,title,newsTime,thumbnail}）
说明：newsnow 用非贪婪正则抓 `};`，遇到嵌套对象容易截断；这里改成**花括号配对扫描**，
      更稳且同为标准库。规范第 4 条：无热度字段 → heat=None。
"""
from __future__ import annotations

import json

from .base import Item

SRC_ID = "ifeng"
NAME = "凤凰网热点"
CATEGORY = "综合"

URL = "https://www.ifeng.com/"
_ANCHOR = "var allData"


def _extract_object(text: str, anchor: str, limit: int = 4_000_000) -> dict | None:
    """从 anchor 之后找第一个 '{'，用花括号配对扫描出完整 JSON 对象。"""
    start = text.find(anchor)
    if start < 0:
        return None
    brace = text.find("{", start)
    if brace < 0:
        return None
    depth, in_str, esc = 0, False, False
    for i in range(brace, min(len(text), brace + limit)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[brace:i + 1])
                except Exception:  # noqa: BLE001
                    return None
    return None


def fetch(client):
    html = client.get_text(URL)
    data = _extract_object(html, _ANCHOR)
    if not isinstance(data, dict):
        raise RuntimeError("凤凰网页面未找到可解析的 allData（改版或被拦）")
    hot = data.get("hotNews1") or []
    if not hot:
        raise RuntimeError("凤凰网 allData.hotNews1 为空（改版或被拦）")

    out: list[Item] = []
    for i, k in enumerate(hot, 1):
        title = (k.get("title") or "").strip()
        url = (k.get("url") or "").strip()
        if not (title and url):
            continue
        out.append(Item(
            ext_id=url,                                   # 用 url 作稳定 id
            title=title,
            url=url,
            rank=i,
            heat=None,                                    # 规范第 4 条
            cover=k.get("thumbnail") or None,
            extra={"newsTime": k.get("newsTime")} if k.get("newsTime") else None,
        ))
    return out
