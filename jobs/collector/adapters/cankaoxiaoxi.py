#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""参考消息 · 三个频道合并

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/cankaoxiaoxi.ts
本文件为 Python 重写，仅使用标准库。

端点（注意是 **http**）：GET http://china.cankaoxiaoxi.com/json/channel/{k}/list.json
      k ∈ {zhongguo, guandian, gj} —— 三路合并后按发布时间降序
规范第 4 条：该源没有热度字段 → heat 保持 None
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .base import Item, clip

SRC_ID = "cankaoxiaoxi"
NAME = "参考消息"
CATEGORY = "综合"

CHANNELS = ("zhongguo", "guandian", "gj")
API = "http://china.cankaoxiaoxi.com/json/channel/{ch}/list.json"
HEADERS = {"Accept": "application/json, text/plain, */*", "Referer": "http://china.cankaoxiaoxi.com/"}


def _ts(s: str | None) -> int | None:
    """'2026-10-18 20:49:24'（北京时间，项目时区规范 +8）→ epoch 秒"""
    if not s:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return int(datetime.strptime(s.strip(), fmt)
                       .replace(tzinfo=timezone(timedelta(hours=8))).timestamp())
        except Exception:  # noqa: BLE001
            continue
    return None


def fetch(client):
    merged: list[tuple[int, Item]] = []
    ok = 0
    for ch in CHANNELS:
        try:
            payload = client.get_json(API.format(ch=ch), headers=HEADERS)
        except Exception:  # noqa: BLE001 —— 单频道失败不影响其他两个
            continue
        rows = (payload or {}).get("list") or []
        if rows:
            ok += 1
        for x in rows:
            d = x.get("data") or {}
            title = (d.get("title") or "").strip()
            if not title:
                continue
            ts = _ts(d.get("publishTime") or d.get("createtime"))
            merged.append((ts or 0, Item(
                ext_id=str(d.get("id") or d.get("url") or title[:40]),
                title=title,
                url=d.get("url"),
                rank=None,                                  # 合并排序后统一回填
                heat=None,                                  # 无热度字段（规范第 4 条）
                desc=clip(d.get("description") or d.get("brief"), 300),
                timestamp=ts,
            )))
    if ok == 0:
        raise RuntimeError("参考消息三个频道全部失败（站点不可达或改版）")

    merged.sort(key=lambda t: t[0], reverse=True)           # 按时间降序（与 newsnow 一致）
    out: list[Item] = []
    for i, (_, it) in enumerate(merged, 1):
        it.rank = i
        out.append(it)
    return out
