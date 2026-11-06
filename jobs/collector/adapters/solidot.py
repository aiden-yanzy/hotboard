#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Solidot · 奇客资讯（newsnow 独有源之一，本次迁移试点）

数据源：官方 RSS（实测 200 + 17 条）—— **用来验证契约能同时容纳 RSS/XML 形态**。
字段映射：
    link 里的 sid → ext_id（稳定）
    title         → title
    link          → url
    description   → desc（去 HTML + 截断）
    pubDate       → timestamp（RFC822 → epoch）
    heat          → **None**（RSS 没有热度字段；遵守规范第 4 条：宁缺勿造）
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

from .base import Item, clip, strip_html

SRC_ID = "solidot"
NAME = "Solidot"
CATEGORY = "科技"

FEED = "https://www.solidot.org/index.rss"
HEADERS = {"Accept": "application/rss+xml, application/xml, text/xml, */*"}


def _epoch(pub: str | None) -> int | None:
    if not pub:
        return None
    try:
        return int(parsedate_to_datetime(pub.strip()).timestamp())
    except Exception:  # noqa: BLE001 —— 时间解析失败不影响条目本身
        return None


def fetch(client):
    raw = client.get_text(FEED, headers=HEADERS)
    # 内容形状校验：不能只信 HTTP 200（WAF/登录页也会是 200）
    if "<rss" not in raw[:600] and "<feed" not in raw[:600]:
        raise RuntimeError("Solidot 响应不是 RSS（可能被 WAF/跳转拦截）")
    root = ET.fromstring(raw)

    rows: list[Item] = []
    for i, it in enumerate(root.findall(".//item"), 1):
        title = (it.findtext("title") or "").strip()
        link = (it.findtext("link") or "").strip()
        if not title:
            continue
        ext = link.split("sid=")[-1] if "sid=" in link else (link or str(i))
        rows.append(Item(
            ext_id=ext,
            title=title,
            url=link or None,
            rank=i,
            heat=None,                       # 规范第 4 条：RSS 无热度 → None
            desc=clip(strip_html(it.findtext("description")), 300),
            timestamp=_epoch(it.findtext("pubDate")),
        ))
    return rows
