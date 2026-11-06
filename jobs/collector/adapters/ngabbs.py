#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""NGA · 帖子列表

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/ngabbs.ts
本文件为 Python 重写，仅使用标准库。

端点：POST https://ngabbs.com/nuke.php?__lib=load_topic&__act=load_topic_reply_ladder2&opt=1&all=1
      body（表单）：__output=14
⚠️ 必须伪装 NGA App：`X-User-Agent: NGA_skull/…` + `User-Agent: Apifox/1.0.0`，
   body 与 Content-Length 都要精确，缺一就返回空
响应：{code, result:[[{tid,subject,author,replies,postdate(秒),tpcurl}]]} → 取 result[0]
热度：`replies`（回复数，0~上千）→ **真热度**
"""
from __future__ import annotations

from .base import Item, num, ts_ms

SRC_ID = "ngabbs"
NAME = "NGA"
CATEGORY = "社区"

API = "https://ngabbs.com/nuke.php?__lib=load_topic&__act=load_topic_reply_ladder2&opt=1&all=1"
HEADERS = {
    "Accept": "*/*",
    "Referer": "https://ngabbs.com/",
    "Accept-Language": "zh-Hans-CN;q=1",
    "User-Agent": "Apifox/1.0.0 (https://apifox.com)",
    "X-User-Agent": "NGA_skull/7.3.1(iPhone13,2;iOS 17.2.1)",
}


def fetch(client):
    payload = client.post_json(API, {"__output": "14"}, headers=HEADERS, form=True)
    res = (payload or {}).get("result") or []
    rows = res[0] if res and isinstance(res[0], list) else []
    if not rows:
        raise RuntimeError(f"NGA result 为空（code={(payload or {}).get('code')}，多因 UA/头不匹配）")

    out: list[Item] = []
    for x in rows:
        title = (x.get("subject") or "").strip()
        tid = x.get("tid")
        if not (title and tid):
            continue
        tpcurl = x.get("tpcurl") or ""
        out.append(Item(
            ext_id=str(tid),
            title=title,
            url=(f"https://bbs.nga.cn{tpcurl}" if tpcurl.startswith("/") else
                 (tpcurl or f"https://bbs.nga.cn/read.php?tid={tid}")),
            rank=len(out) + 1,
            heat=num(x.get("replies")),                     # 回复数 = 真热度
            author=x.get("author") or None,
            timestamp=ts_ms(x.get("postdate")),
        ))
    return out
