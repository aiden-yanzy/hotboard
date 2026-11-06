#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快手 · 热榜（从首页内嵌 Apollo state 抠）

抓取逻辑移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）apps/engine/src/routes/kuaishou.ts
本文件为 Python 重写，仅使用标准库。

端点：GET https://www.kuaishou.com/?isHome=1（HTML，数据在 `window.__APOLLO_STATE__`）
解析步骤（照抄上游，勿改）：
  1. 取 `window.__APOLLO_STATE__=` 之后的片段
  2. 截断点 = min(`;(function(`, `</script>`)；再去掉尾部非法字符，**截到最后一个 `}`**
  3. json.loads → ["defaultClient"]；榜单在
     `$ROOT_QUERY.visionHotRank({"page":"home"})`，兜底带 platform 的变体
  4. 每项 item.id → client[id] 取 {name,poster,hotValue,photoIds.json[]}
热度：`hotValue` 形如 "1215.4万" → `cn_num()` 解析（10⁷ 量级）；**可能为 null → 判空**
条目 id/url：用 `photoIds.json[0]`（不是 item.id）
"""
from __future__ import annotations

import json
import re
import urllib.parse

from .base import Item, cn_num

SRC_ID = "kuaishou"
NAME = "快手热榜"
CATEGORY = "娱乐"

URL = "https://www.kuaishou.com/?isHome=1"
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"),
}
_MARK = "window.__APOLLO_STATE__="


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    i = html.find(_MARK)
    if i < 0:
        raise RuntimeError("快手首页未找到 __APOLLO_STATE__（改版或被拦）")
    body = html[i + len(_MARK):]
    cuts = [c for c in (body.find(";(function("), body.find("</script>")) if c > 0]
    if cuts:
        body = body[:min(cuts)]
    body = body.strip().rstrip(";").strip()
    body = body[:body.rfind("}") + 1]              # 尾部可能有非法字符
    try:
        state = json.loads(body)
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"快手 Apollo state 解析失败：{type(e).__name__}") from e

    client_state = state.get("defaultClient") or {}
    rank_key = next((k for k in client_state
                     if k.startswith("$ROOT_QUERY.visionHotRank") and '"page":"home"' in k.replace('\\"', '"')), None)
    if not rank_key:
        raise RuntimeError("快手 Apollo state 里没有 visionHotRank（结构已变）")
    items = (client_state.get(rank_key) or {}).get("items") or []

    out: list[Item] = []
    for it in items:
        node = client_state.get((it or {}).get("id") or (it or {}).get("__ref") or "") or {}
        name = (node.get("name") or "").strip()
        if not name:
            continue
        photo_ids = ((node.get("photoIds") or {}).get("json") or [])
        pid = photo_ids[0] if photo_ids else None
        poster = node.get("poster") or ""
        out.append(Item(
            ext_id=str(pid or name[:30]),
            title=name,
            url=f"https://www.kuaishou.com/short-video/{pid}" if pid else None,
            rank=len(out) + 1,
            heat=cn_num(node.get("hotValue")),               # "1215.4万" → 12154000
            cover=urllib.parse.unquote(poster) if poster else None,
        ))
    if not out:
        raise RuntimeError("快手热榜解析出 0 条（结构已变）")
    return out
