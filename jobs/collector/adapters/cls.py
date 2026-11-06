#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""财联社 · 电报（署名接口）

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/cls/{index,utils}.ts
本文件为 Python 重写，仅使用标准库（hashlib 代替 WebCrypto）。

签名算法（已在源码与实测双重核对）：
    qs   = 把 {appName, os, sv, ...extra} 按 key 字母序排序后拼成 "k=v&k=v"
    sign = md5( sha1_hex(qs) )          # 注意：先 SHA-1 取小写 hex，再对该 hex 做 MD5
    请求 = "<qs>&sign=<sign>"           # sign 追加在末尾，不参与排序
端点：GET https://www.cls.cn/v1/roll/get_roll_list?<qs>&sign=<sign>
      ⚠️ 必须用 **v1** 路径（v3 会返回 errno:50101 加载中）
额外参数：last_time=<秒>、refresh_type=1、rn=30；头需 Referer: https://www.cls.cn/telegraph
规范第 4 条：电报无热度字段 → heat=None（真正的排行榜在 cls-hot 子源，未在本适配器实现）
"""
from __future__ import annotations

import hashlib
import time

from .base import Item, clip, strip_html

SRC_ID = "cls"
NAME = "财联社电报"
CATEGORY = "财经"

BASE_PARAMS = {"appName": "CailianpressWeb", "os": "web", "sv": "7.7.5"}
API = "https://www.cls.cn/v1/roll/get_roll_list"
HEADERS = {"Referer": "https://www.cls.cn/telegraph",
           "Accept": "application/json, text/plain, */*"}


def _signed_query(extra: dict) -> str:
    params = {**BASE_PARAMS, **extra}
    qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
    sign = hashlib.md5(hashlib.sha1(qs.encode("utf-8")).hexdigest().encode("utf-8")).hexdigest()
    return f"{qs}&sign={sign}"


def fetch(client):
    qs = _signed_query({"last_time": int(time.time()), "refresh_type": 1, "rn": 30})
    payload = client.get_json(f"{API}?{qs}", headers=HEADERS)
    if not isinstance(payload, dict):
        raise RuntimeError("财联社响应不是 JSON（签名或路径已被变更）")
    if payload.get("errno") not in (0, None):
        raise RuntimeError(f"财联社返回 errno={payload.get('errno')} msg={payload.get('msg')}"
                           "（签名失效或需 v1 路径的提示）")

    roll = ((payload.get("data") or {}).get("roll_data")) or []
    if not roll:
        raise RuntimeError("财联社 roll_data 为空（形状可能已变）")

    out: list[Item] = []
    for i, k in enumerate(roll, 1):
        if k.get("is_ad"):
            continue                                      # 与 newsnow 一致：过滤广告
        title = (k.get("title") or k.get("brief") or "").strip()
        if not title:
            continue
        kid = k.get("id")
        ctime = k.get("ctime")
        out.append(Item(
            ext_id=str(kid or i),
            title=title[:120],
            url=f"https://www.cls.cn/detail/{kid}" if kid else k.get("shareurl"),
            rank=i,
            heat=None,                                    # 规范第 4 条
            desc=clip(strip_html(k.get("brief")), 300),
            timestamp=int(ctime) if str(ctime).isdigit() else None,
        ))
    return out
