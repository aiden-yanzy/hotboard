#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""酷安 Coolapk · 今日热门

⚠️ 本文件的 **X-App-Token 算法移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）**
   `src/utils/getToken/coolapk.ts` + `src/routes/coolapk.ts`（保留出处声明，符合 MIT 要求）。
   除 token 生成外，请求/解析为本项目用标准库重写。

端点：GET https://api.coolapk.com/v6/page/dataList?url=/feed/statList?cacheExpires=300
        &statType=day&sortField=detailnum&title=今日热门&subTitle=&page=1
必需头：X-App-Id / X-App-Token（按设备ID+时间戳生成）/ X-Api-Version / 移动端 UA 等
响应：{data:[{id, message(正文), tpic(封面), username, ttitle, shareUrl}]}
热度：**上游也没有热度**（DailyHotApi 里 `hot: undefined`）→ 按本规范 heat=None（不造假）
⚠️ 该接口有风控：若返回非 200 或 data 为空，视为被拒（不重试轰炸）
"""
from __future__ import annotations

import base64
import hashlib
import random
import string
import time

from .base import Item, clip

SRC_ID = "coolapk"
NAME = "酷安今日热门"
CATEGORY = "社区"

API = ("https://api.coolapk.com/v6/page/dataList"
       "?url=/feed/statList?cacheExpires=300&statType=day&sortField=detailnum"
       "&title=%E4%BB%8A%E6%97%A5%E7%83%AD%E9%97%A8&subTitle=&page=1")


def _md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _device_id() -> str:
    """随机设备ID：5 段 base36，长度 [10,6,6,6,14]，用 - 连接（同上游算法）。"""
    alphabet = string.digits + string.ascii_lowercase
    return "-".join("".join(random.choice(alphabet) for _ in range(n)) for n in (10, 6, 6, 6, 14))


def _app_token() -> str:
    """酷安 X-App-Token（移植自 DailyHotApi 的 get_app_token）。"""
    device_id = _device_id()
    now = int(time.time())
    hex_now = "0x" + format(now, "x")
    s = ("token://com.coolapk.market/c67ef5943784d09750dcfbb31020f0ab?"
         + _md5(str(now)) + "$" + device_id + "&com.coolapk.market")
    md5_s = _md5(base64.b64encode(s.encode("utf-8")).decode("ascii"))
    return md5_s + device_id + hex_now


def _headers() -> dict:
    return {
        "X-Requested-With": "XMLHttpRequest",
        "X-App-Id": "com.coolapk.market",
        "X-App-Token": _app_token(),
        "X-Sdk-Int": "29",
        "X-Sdk-Locale": "zh-CN",
        "X-App-Version": "11.0",
        "X-Api-Version": "11",
        "X-App-Code": "2101202",
        "Accept": "application/json, text/plain, */*",
        "User-Agent": ("Mozilla/5.0 (Linux; Android 10; Mi 10) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/111.0.5563.15 Mobile Safari/537.36"),
    }


def fetch(client):
    payload = client.get_json(API, headers=_headers())
    rows = (payload or {}).get("data") or []
    if not rows:
        raise RuntimeError(f"酷安热榜为空（被风控或改版；message={(payload or {}).get('message')}）")

    out: list[Item] = []
    for i, x in enumerate(rows, 1):
        text = (x.get("message") or "").strip()
        if not text:
            continue
        url = x.get("shareUrl") or ""
        if url.startswith("//"):
            url = "https:" + url
        out.append(Item(
            ext_id=str(x.get("id") or i),
            title=clip(text, 120) or text[:120],
            url=url or f"https://www.coolapk.com/feed/{x.get('id')}",
            rank=i,
            heat=None,                                      # 上游同样无热度 → 不造假
            desc=clip(x.get("ttitle"), 300),
            cover=x.get("tpic") or None,
            author=x.get("username") or None,
        ))
    return out
