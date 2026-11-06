#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""博客园 · 10 天推荐排行

来源：参照站 rebang.today 有此源（`cnblogs`）而我们没有 → 实测后自研。
⚠️ 自行实测写出（未参考第三方聚合项目代码；RSSHub 的 /cnblogs 路由是 AGPL，未使用）。

端点：GET https://www.cnblogs.com/aggsite/topdiggs（HTML，服务端渲染）
解析：按 `/p/<数字>` 文章链接抓取，排除站点导航类链接；`rank` 用出现顺序
热度：⭐ 部分条目带 `title="评论7, 推荐6, 阅读1782"`（编辑推荐/最多推荐卡片）
      → 解析出**阅读数**作为 heat；普通榜单项没有该属性 → heat=None（宁缺勿造）
⚠️ 官方 feed（feed.cnblogs.com/blog/sitehome/*）实测全 500（已停用），不要改回 feed 方案
"""
from __future__ import annotations

import re

from .base import Item, num

SRC_ID = "cnblogs"
NAME = "博客园"
CATEGORY = "开发"

URL = "https://www.cnblogs.com/aggsite/topdiggs"
HEADERS = {"Referer": "https://www.cnblogs.com/", "Accept": "text/html,application/xhtml+xml,*/*"}
_ARTICLE = re.compile(r'<a[^>]+href="(https?://www\.cnblogs\.com/[^"/]+/p/\d+[^"]*)"[^>]*>(.*?)</a>', re.S)
_COUNT = re.compile(r'title="评论(\d+),\s*推荐(\d+),\s*阅读(\d+)"')
# 导航/推荐位链接（非榜单条目），按 URL 片段排除
_SKIP = ("/cmt/p/", "/aggsite/", "candidate", "sponsor")

# 榜单条目要求链接「紧邻」一个统计属性或处于列表结构中；这里用顺序 + 去重 + 排除法
def _txt(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", s or "")).strip()


def fetch(client):
    html = client.get_text(URL, headers=HEADERS)
    rows: list[tuple[str, str, int | None]] = []
    seen: set[str] = set()
    for m in _ARTICLE.finditer(html):
        url, inner = m.group(1), _txt(m.group(2))
        if not inner or len(inner) < 6:
            continue
        if any(s in url for s in _SKIP):
            continue
        key = url.rstrip("/")
        if key in seen:
            continue
        # 取该 <a> 标签自身（回看 200 字符）里的统计属性
        start = max(0, m.start() - 220)
        near = html[start:m.end()]
        c = None
        for cm in _COUNT.finditer(near):
            c = num(cm.group(3))                            # 阅读数当热度
        seen.add(key)
        rows.append((url, inner, c))
    if len(rows) < 5:
        raise RuntimeError(f"博客园榜单解析到的条目过少（{len(rows)} 条，可能改版）")

    out: list[Item] = []
    for i, (url, title, rd) in enumerate(rows[:30], 1):
        pid = re.search(r"/p/(\d+)", url)
        out.append(Item(
            ext_id=pid.group(1) if pid else url,
            title=title[:120],
            url=url,
            rank=i,
            heat=rd,                                        # 有则阅读数，无则 None
        ))
    return out
