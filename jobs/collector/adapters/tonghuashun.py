#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""同花顺 · 股票热榜

来源：参照站 rebang.today 有此源（`tonghuashun`）而我们没有 → 实测端点后自研。
⚠️ 本文件为**自行实测**写出（未参考任何第三方聚合项目的代码）。

端点：GET https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock
        ?stock_type=a&type=hour&list_type=normal
响应：{status_code:0, data:{stock_list:[{order,market,code,name,rate,rise_and_fall,hot_rank_chg,tag}]}}
热度：⭐ `rate`（同花顺热度值，实测 10⁵~10⁶ 量级）→ **真热度**
rank：`order` 字段（1 开始）
⚠️ `rate` 是浮点字符串量级（1227756.0）→ num() 归一为 int
"""
from __future__ import annotations

from .base import Item, num

SRC_ID = "tonghuashun"
NAME = "同花顺热榜"
CATEGORY = "财经"

API = ("https://dq.10jqka.com.cn/fuyao/hot_list_data/out/hot_list/v1/stock"
       "?stock_type=a&type=hour&list_type=normal")
HEADERS = {"Referer": "https://eq.10jqka.com.cn/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    if (payload or {}).get("status_code") != 0:
        raise RuntimeError(f"同花顺返回非 0 状态：{payload.get('status_code')} {payload.get('status_msg')}")
    rows = ((payload or {}).get("data") or {}).get("stock_list") or []
    if not rows:
        raise RuntimeError("同花顺 stock_list 为空（改版或被拦）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        name = (x.get("name") or "").strip()
        code = x.get("code")
        if not (name and code):
            continue
        tag = x.get("tag") or {}
        concepts = tag.get("concept_tag") if isinstance(tag, dict) else None
        out.append(Item(
            ext_id=str(code),
            title=name,
            url=f"https://stockpage.10jqka.com.cn/{code}/",
            rank=num(x.get("order")) or i,
            heat=num(x.get("rate")),                        # 热度值 = 真热度
            desc="、".join(concepts) if isinstance(concepts, list) and concepts else None,
            extra={"涨跌幅": x.get("rise_and_fall")} if x.get("rise_and_fall") is not None else None,
        ))
    return out
