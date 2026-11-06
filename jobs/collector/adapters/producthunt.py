#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Product Hunt · 每日精选（走 Atom feed，免 token）

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/producthunt.ts
本文件为 Python 重写，仅使用标准库。

newsnow 有两条路径：
  ① GraphQL（需 `PRODUCTHUNT_API_TOKEN`，能拿到 votesCount）
  ② Atom feed 回退（`https://www.producthunt.com/feed`，**免 token**）
本适配器选 ②：本项目不引入外部 token 依赖（采集器镜像原则：少依赖=少坏面）。
⚠️ 实测该 feed 是 **Atom（<feed><entry>）而不是 RSS**，解析时走 Atom 命名空间。
规范第 4 条：Atom 里没有投票数 → heat=None
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

from .base import Item, clip, strip_html

SRC_ID = "producthunt"
NAME = "Product Hunt"
CATEGORY = "开发"

FEED = "https://www.producthunt.com/feed"
HEADERS = {"Accept": "application/atom+xml, application/xml, text/xml, */*"}
ATOM = {"a": "http://www.w3.org/2005/Atom"}


def fetch(client):
    raw = client.get_text(FEED, headers=HEADERS)
    if "<feed" not in raw[:800]:
        raise RuntimeError("Product Hunt feed 不是 Atom（可能被拦或改版）")
    root = ET.fromstring(raw)
    entries = root.findall("a:entry", ATOM) or root.findall(".//entry")
    if not entries:
        raise RuntimeError("Product Hunt Atom 解析为空")

    out: list[Item] = []
    for i, e in enumerate(entries, 1):
        title = (e.findtext("a:title", default="", namespaces=ATOM) or "").strip()
        if not title:
            continue
        link_el = e.find("a:link", ATOM)
        link = (link_el.get("href") if link_el is not None else None) or \
               (e.findtext("a:id", default="", namespaces=ATOM) or "").strip()
        summary = e.findtext("a:summary", default="", namespaces=ATOM) or \
                  e.findtext("a:content", default="", namespaces=ATOM)
        out.append(Item(
            ext_id=(e.findtext("a:id", default="", namespaces=ATOM) or link or str(i)).strip(),
            title=title,
            url=link or None,
            rank=i,
            heat=None,                                    # Atom 无投票数（规范第 4 条）
            desc=clip(strip_html(summary), 300),
            timestamp=None,
        ))
    return out
