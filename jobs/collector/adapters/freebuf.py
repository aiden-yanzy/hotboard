#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FreeBuf · RSS 资讯

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/freebuf.ts
本文件为 Python 重写，仅使用标准库（xml.etree 代替 fast-xml-parser）。

端点：GET https://www.freebuf.com/feed（RSS 2.0）
要点：该 feed **没有 <guid>**，所以 id 取 link；解析为空必须**抛错**（识别 WAF 挑战页，避免缓存空列表）
规范第 4 条：RSS 无热度字段 → heat=None
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .base import Item, clip, strip_html

SRC_ID = "freebuf"
NAME = "FreeBuf"
CATEGORY = "科技"

FEED = "https://www.freebuf.com/feed"
HEADERS = {"Accept": "application/rss+xml, application/xml, text/xml, */*",
           "Referer": "https://www.freebuf.com/"}


def _epoch(pub: str | None) -> int | None:
    if not pub:
        return None
    try:
        return int(parsedate_to_datetime(pub.strip()).timestamp())
    except Exception:  # noqa: BLE001
        return None


def _text(node, tag: str) -> str:
    if node is None:
        return ""
    found = node.find(tag)
    return (found.text or "").strip() if found is not None and found.text else ""


def _looks_like_feed(raw: str) -> bool:
    head = raw[:800]
    return "<rss" in head or "<feed" in head


def fetch(client):
    raw = client.get_text(FEED, headers=HEADERS)
    if not _looks_like_feed(raw):
        # 实测：本站对 urllib 会下发阿里云 WAF 挑战页（HTTP 200 + html），curl 能过 → 走兜底
        raw = client.get_text_curl(FEED, headers=HEADERS)
    if not _looks_like_feed(raw):
        raise RuntimeError("FreeBuf 响应不是 RSS（WAF/CF 挑战页，且 curl 兜底也没拿到）")
    items = ET.fromstring(raw).findall(".//item")
    if not items:
        raise RuntimeError("FreeBuf RSS 解析为空（可能被挑战页替换，按 newsnow 的做法抛错）")

    out: list[Item] = []
    for i, it in enumerate(items, 1):
        title = _text(it, "title")
        link = _text(it, "link")
        guid = _text(it, "guid")
        if not (title and link):
            continue
        out.append(Item(
            ext_id=guid or link,                          # 该 feed 无 guid → 用 link
            title=title,
            url=link,
            rank=i,
            heat=None,                                    # 规范第 4 条
            desc=clip(strip_html(_text(it, "description")), 300),
            timestamp=_epoch(_text(it, "pubDate")),
        ))
    return out
