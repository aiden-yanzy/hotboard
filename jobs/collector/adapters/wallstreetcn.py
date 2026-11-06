#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""华尔街见闻 · 7x24 快讯（newsnow 独有源之一，本次迁移试点）

数据源：api-one.wallstcn.com 公开 JSON 接口（实测 200 + 20 条）
字段映射：
    id            → ext_id（源内稳定 id）
    title/content → title（快讯常常没有 title，取正文前段）
    uri           → url
    content_text  → desc（截断 300 字）
    display_time  → timestamp（unix 秒）
    score         → heat（**为 0 时按"没有热度"处理 → None**，遵守规范第 4 条）
"""
from __future__ import annotations

from .base import Item, clip, num

SRC_ID = "wallstreetcn"
NAME = "华尔街见闻"
CATEGORY = "财经"

API = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=30"
HEADERS = {"Accept": "application/json", "Referer": "https://wallstreetcn.com/live/global"}


def _ts(x):
    s = str(x or "").strip()
    return int(s) if s.isdigit() and len(s) >= 9 else None


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    if not isinstance(payload, dict) or payload.get("code") not in (20000, 200, 0, None):
        # 内容形状校验：不能只信 HTTP 200（雪球就是 200 却返回 WAF 页面）
        raise RuntimeError(f"华尔街见闻响应异常：code={payload.get('code')} message={payload.get('message')}")

    rows: list[Item] = []
    for i, x in enumerate(((payload.get("data") or {}).get("items") or []), 1):
        title = (x.get("title") or x.get("content_text") or "").strip()
        if not title:
            continue
        score = num(x.get("score"))
        rows.append(Item(
            ext_id=str(x.get("id") or i),
            title=title[:120],
            url=x.get("uri") or (f"https://wallstreetcn.com/livenews/{x.get('id')}" if x.get("id") else None),
            rank=i,
            # ⚠️ 规范第 4 条：这里**故意不把 score 当 heat** ——
            #    score 是站内权重（实测多为 0~2），不是热度量级，填进 snapshots.heat 会让
            #    涨跌/趋势彻底失去意义。它放 extra 里保留原值，heat 保持 None。
            heat=None,
            desc=clip(x.get("content_text"), 300),
            timestamp=_ts(x.get("display_time")),
            extra={"score": score} if score else None,
        ))
    return rows
