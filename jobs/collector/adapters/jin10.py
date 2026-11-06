#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""金十数据 · 快讯

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/jin10.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.jin10.com/flash_newest.js?t=<毫秒时间戳>
响应是 JS 文本：`var newest = [ ... ];` → 去前后缀后当 JSON 解析
过滤：保留有 (data.title || data.content) 且 channel 不含 5 的条目
规范第 4 条：快讯没有热度字段 → heat 保持 None
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timedelta, timezone

from .base import Item, clip

SRC_ID = "jin10"
NAME = "金十数据"
CATEGORY = "财经"

API = "https://www.jin10.com/flash_newest.js"
HEADERS = {"Referer": "https://www.jin10.com/", "Accept": "*/*"}

_PREFIX = re.compile(r"^var\s+newest\s*=\s*")
_BRACKET = re.compile(r"^【([^】]*)】(.*)$", re.S)


def _ts(s: str | None) -> int | None:
    """'2026-10-19 11:19:54'（**北京时间**，按项目时区规范 +8）→ epoch 秒"""
    if not s:
        return None
    try:
        dt = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone(timedelta(hours=8)))
        return int(dt.timestamp())
    except Exception:  # noqa: BLE001
        return None


def fetch(client):
    raw = client.get_text(f"{API}?t={int(time.time() * 1000)}", headers=HEADERS)
    body = _PREFIX.sub("", raw.strip()).rstrip(";").strip()
    if not body.startswith("["):
        raise RuntimeError("金十响应不是 flash_newest 数组（可能被拦或改版）")
    rows = json.loads(body)

    out: list[Item] = []
    for i, k in enumerate(rows, 1):
        data = k.get("data") or {}
        text = (data.get("title") or data.get("content") or "").replace("<b>", "").replace("</b>", "")
        text = re.sub(r"\s+", " ", text).strip()
        if not text:
            continue
        if isinstance(k.get("channel"), list) and 5 in k["channel"]:
            continue                                   # 与 newsnow 一致：channel 含 5 的不要
        m = _BRACKET.match(text)
        title = (m.group(1).strip() if m else text)[:120]
        hover = (m.group(2).strip() if m else None)
        kid = k.get("id")
        out.append(Item(
            ext_id=str(kid or i),
            title=title or text[:120],
            url=f"https://flash.jin10.com/detail/{kid}" if kid else None,
            rank=i,
            heat=None,                                 # 快讯无热度（规范第 4 条）
            desc=clip(hover or text, 300),
            timestamp=_ts(k.get("time")),
            extra={"important": 1} if k.get("important") else None,
        ))
    return out
