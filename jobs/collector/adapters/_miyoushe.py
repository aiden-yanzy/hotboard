#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""米游社系（原神 / 崩坏3 / 星穹铁道 / 米游社）共用抓取逻辑

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/{genshin,honkai,starrail,miyoushe}.ts
本文件为 Python 重写，仅使用标准库。

⚠️ 本文件**不是适配器**（没有 SRC_ID，注册表会自动跳过），只给上面四个源共用：
   bbs-api-static.miyoushe.com/painter/wapi/getNewsList?client_type=4&gids={gids}&...
   gids: 1=崩坏3 / 2=原神 / 6=星穹铁道；米游社路由用 game 参数（1~8）同源
⚠️ 实测 `post.view_status` 恒为 0/1（是状态位，不是阅读数）→ **heat 一律 None**
   （规范第 4 条：宁缺勿造；上游拿它当热度是错的，本项目不跟着错）
"""
from __future__ import annotations

from .base import Item, clip, ts_ms

API = ("https://bbs-api-static.miyoushe.com/painter/wapi/getNewsList"
       "?client_type=4&gids={gids}&last_id=&page_size={size}&type={ntype}")
HEADERS = {"Referer": "https://www.miyoushe.com/", "Accept": "application/json, text/plain, */*"}


def fetch_news(client, gids: int, url_prefix: str, size: int = 20) -> list[Item]:
    payload = client.get_json(API.format(gids=gids, size=size, ntype=1), headers=HEADERS)
    data = (payload or {}).get("data") or {}
    rows = data.get("list") or data.get("data") or []
    if not rows:
        raise RuntimeError(f"米游社 gids={gids} 返回空（retcode={(payload or {}).get('retcode')}）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        p = x.get("post") or {}
        title = (p.get("subject") or "").strip()
        pid = p.get("post_id")
        if not (title and pid):
            continue
        cover = p.get("cover")
        if not cover:
            imgs = p.get("images") or []
            cover = imgs[0] if imgs else None
        user = x.get("user") or {}
        out.append(Item(
            ext_id=str(pid),
            title=title,
            url=f"{url_prefix}{pid}",
            rank=i,
            heat=None,                                      # view_status 是状态位，不是热度
            desc=clip(p.get("content"), 300),
            cover=cover or None,
            author=user.get("nickname") if isinstance(user, dict) else None,
            timestamp=ts_ms(p.get("created_at")),
        ))
    return out
