#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Steam · 当前在线人数榜

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/steam.ts
本文件为 Python 重写，仅使用标准库（采集器镜像约定：少依赖=少坏面）。

端点：GET https://store.steampowered.com/stats/stats/（HTML，无分页）
解析：每行 <tr class="player_count_row"> 里取游戏链接、名称、当前在线人数
规范第 4 条：在线人数是"信息"不是"热度" → 放 extra，heat 保持 None
"""
from __future__ import annotations

import re

from .base import Item, num

SRC_ID = "steam"
NAME = "Steam 在线榜"
CATEGORY = "娱乐"

URL = "https://store.steampowered.com/stats/stats/"
_ROW = re.compile(r'<tr[^>]*player_count_row[^>]*>(.*?)</tr>', re.S)
_HREF = re.compile(r'<a[^>]+class="gameLink"[^>]+href="([^"]+)"')
_NAME = re.compile(r'<a[^>]+class="gameLink"[^>]*>(.*?)</a>', re.S)
_CUR = re.compile(r'class="currentServers"[^>]*>([\d,]+)<')


def fetch(client):
    html = client.get_text(URL)
    # 规范第 5 条：校验内容形状（该站偶发返回 0 字节 / CDN 限流页）
    rows = _ROW.findall(html)
    if not rows:
        raise RuntimeError("Steam 统计页未匹配到 player_count_row（CDN 空响应或页面改版）")

    out: list[Item] = []
    for i, row in enumerate(rows, 1):
        m_href = _HREF.search(row)
        m_name = _NAME.search(row)
        if not (m_href and m_name):
            continue
        title = re.sub(r"<[^>]+>", "", m_name.group(1)).strip()
        if not title:
            continue
        url = m_href.group(1)
        m_cur = _CUR.search(row)
        cur = num(m_cur.group(1)) if m_cur else None
        out.append(Item(
            ext_id=url,                      # 该源没有稳定数字 id，用 url（跨轮次稳定）
            title=title,
            url=url,
            rank=i,
            heat=None,                       # 在线人数≠热度，不污染 snapshots.heat
            extra={"online": cur, "src_note": "steam-stats"} if cur else None,
        ))
    return out
