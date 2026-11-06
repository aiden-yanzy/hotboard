#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""牛客 · 热榜

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/nowcoder.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://gw-c.nowcoder.com/api/sparta/hot-search/top-hot-pc?size=20&t=
      （`_` 传毫秒时间戳防缓存）
字段：data.result[] → type/id/uuid/title/hotValueFromDolphin
⚠️ url 需按 type 分流：74 → /feed/main/detail/{uuid}；0 → /discuss/{id}；其他 type 无 url（跳过）
"""
from __future__ import annotations

import time

from .base import Item, num

SRC_ID = "nowcoder"
NAME = "牛客热榜"
CATEGORY = "开发"

API = "https://gw-c.nowcoder.com/api/sparta/hot-search/top-hot-pc?size=20&t="
HEADERS = {"Accept": "application/json, text/plain, */*", "Referer": "https://www.nowcoder.com/"}


def fetch(client):
    url = f"{API}&_={int(time.time() * 1000)}"
    payload = client.get_json(url, headers=HEADERS)
    if not isinstance(payload, dict) or not payload.get("success", True):
        raise RuntimeError(f"牛客响应异常：code={payload.get('code') if isinstance(payload, dict) else '?'} "
                           f"msg={payload.get('msg') if isinstance(payload, dict) else '?'}")
    result = ((payload.get("data") or {}).get("result")) or []
    if not result:
        raise RuntimeError("牛客热榜返回空列表（形状可能已变）")

    out: list[Item] = []
    for i, k in enumerate(result, 1):
        title = (k.get("title") or "").strip()
        if not title:
            continue
        t = k.get("type")
        if t == 74:                                   # 帖子
            ext_id, link = str(k.get("uuid") or i), f"https://www.nowcoder.com/feed/main/detail/{k.get('uuid')}"
        elif t == 0:                                  # 讨论
            ext_id, link = str(k.get("id") or i), f"https://www.nowcoder.com/discuss/{k.get('id')}"
        else:                                         # 其他类型没有可用链接 → 跳过（规范：不要产出坏条目）
            continue
        hv = num(k.get("hotValueFromDolphin"))
        out.append(Item(
            ext_id=ext_id,
            title=title,
            url=link,
            rank=i,
            heat=hv if hv else None,                  # 0/缺失 → None（规范第 4 条）
        ))
    return out
