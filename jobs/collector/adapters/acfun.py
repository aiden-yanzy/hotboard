#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AcFun · 排行榜

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/acfun.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.acfun.cn/rest/pc-direct/rank/channel?channelId={type}&rankLimit=30&rankPeriod=DAY
      type 默认 -1（综合，此时 channelId 传空串）
      ⚠️ 必须带 Referer，否则被拒
响应：rankList[] → {dougaId,contentTitle,contentDesc,userName,contributeTime(ms),likeCount,videoCover}
热度：`likeCount`（点赞数，实测数百）→ 站点口径热度
⚠️ 上游代码读 `v.coverUrl`，实测真实字段是 **videoCover** → 这里按真实字段取
"""
from __future__ import annotations

from .base import Item, clip, num, ts_ms

SRC_ID = "acfun"
NAME = "AcFun排行"
CATEGORY = "娱乐"

API = ("https://www.acfun.cn/rest/pc-direct/rank/channel"
       "?channelId=&rankLimit=30&rankPeriod=DAY")
# ⚠️ 实测坑：channelId 必须传**空串**。写 `channelId=-1`（看着更"像"综合榜）服务端会返回
#    `{"rankList":[]}`（58 字节空壳）；传空串才返回 154KB 的正常榜单。别"顺手改回去"。
HEADERS = {"Referer": "https://www.acfun.cn/rank/list/?cid=-1&pcid=-1&range=DAY",
           "Accept": "application/json, text/plain, */*"}


def fetch(client):
    payload = client.get_json(API, headers=HEADERS)
    rows = (payload or {}).get("rankList") or []
    if not rows:
        raise RuntimeError("AcFun rankList 为空（改版或被拦，检查 Referer）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        title = (x.get("contentTitle") or "").strip()
        ac = x.get("dougaId")
        if not (title and ac):
            continue
        out.append(Item(
            ext_id=str(ac),
            title=title,
            url=f"https://www.acfun.cn/v/ac{ac}",
            rank=i,
            heat=num(x.get("likeCount")),                   # 点赞数（站点口径）
            desc=clip(x.get("contentDesc"), 300),
            cover=x.get("videoCover") or None,              # ⚠️ 不是 coverUrl
            author=x.get("userName") or None,
            timestamp=ts_ms(x.get("contributeTime")),
        ))
    return out
