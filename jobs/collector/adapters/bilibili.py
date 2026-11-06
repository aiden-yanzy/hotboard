#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""哔哩哔哩 · 排行榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/bilibili.ts
本文件为 Python 重写，仅使用标准库。

主端点：GET https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all
        ⚠️ 实测必须带一个 `Cookie: buvid3=<任意值>`，否则返回 code=-352（风控）
备用端点：GET https://api.bilibili.com/x/web-interface/ranking?rid={rid}&type=all
        实测免 cookie、免 wbi 签名，返回 100 条（代价：无 desc/pubdate，热度变弹幕数）
本适配器：主端点失败时自动降级到备用端点（保持"抓得到"优先）。
热度：主端点 `stat.view`（播放量，10⁶~10⁷）→ **真热度**
"""
from __future__ import annotations

from .base import Item, clip, num, ts_ms

SRC_ID = "bilibili"
NAME = "B站排行榜"
CATEGORY = "娱乐"

RID_MAP = {"0": "全站", "1": "动画", "3": "音乐", "4": "游戏", "5": "娱乐", "188": "科技",
           "119": "鬼畜", "129": "舞蹈", "155": "时尚", "160": "生活", "168": "国创",
           "181": "影视"}
API_V2 = "https://api.bilibili.com/x/web-interface/ranking/v2?rid={rid}&type=all"
API_V1 = "https://api.bilibili.com/x/web-interface/ranking?rid={rid}&type=all"
HEADERS = {
    "Referer": "https://www.bilibili.com/ranking/all",
    "Cookie": "buvid3=hotboard-local",      # ⭐ 实测必需，否则 -352
    "Accept": "application/json, text/plain, */*",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}


def _rows_from(payload, rid):
    code = (payload or {}).get("code")
    rows = ((payload or {}).get("data") or {}).get("list") or []
    if code not in (0, None) or not rows:
        raise RuntimeError(f"B站返回 code={code}（风控或形状变化）")
    out: list[Item] = []
    v2 = "owner" in (rows[0] or {})
    for i, x in enumerate(rows, 1):
        title = (x.get("title") or "").strip()
        bvid = x.get("bvid")
        if not (title and bvid):
            continue
        if v2:
            owner = x.get("owner") or {}
            stat = x.get("stat") or {}
            desc, author, heat, pub = x.get("desc"), owner.get("name"), num(stat.get("view")), ts_ms(x.get("pubdate"))
        else:                                   # 备用端点字段
            desc, author, heat, pub = None, x.get("author"), num(x.get("video_review")), None
        cover = (x.get("pic") or "").replace("http://", "https://") or None
        out.append(Item(
            ext_id=str(bvid),
            title=title,
            url=x.get("short_link_v2") or f"https://www.bilibili.com/video/{bvid}",
            rank=i,
            heat=heat,
            desc=clip(desc, 300) or (None if v2 else "该视频暂无简介"),
            cover=cover,
            author=author or None,
            timestamp=pub,
            extra={"rid": rid, "tab": RID_MAP.get(str(rid), str(rid))} if rid is not None else None,
        ))
    return out


def fetch(client):
    rid = "0"
    try:
        return _rows_from(client.get_json(API_V2.format(rid=rid), headers=HEADERS), rid)
    except Exception:                            # noqa: BLE001 —— 风控时降级到备用端点
        return _rows_from(client.get_json(API_V1.format(rid=rid), headers=HEADERS), rid)
