#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""雪球 · 热门股票

抓取逻辑移植自 newsnow（ourongxing/newsnow，MIT License）server/sources/xueqiu.ts
本文件为 Python 重写，仅使用标准库。

两步（关键）：
  1. GET https://xueqiu.com/hq  → 让服务端下发 cookie（xq_a_token / xq_r_token / u）
     （HttpClient 内置 Cookie 罐，同一次运行内自动透传，适配器无需手拼 Cookie 头）
  2. GET https://stock.xueqiu.com/v5/stock/hot_stock/list.json?size=30&_type=10&type=10
⚠️ 实测本机直连常返回 {"error_code":"400016"}（风控）。遇到就给源级错误，
   让它记入 sources.last_err（规范第 5 条），**不要**伪造数据。
规范第 4 条：涨跌幅是行情不是热度 → heat=None
"""
from __future__ import annotations

from .base import Item

SRC_ID = "xueqiu"
NAME = "雪球热股"
CATEGORY = "财经"

WARM = "https://xueqiu.com/hq"
API = "https://stock.xueqiu.com/v5/stock/hot_stock/list.json?size=30&_type=10&type=10"
HEADERS = {"Referer": "https://xueqiu.com/", "Accept": "application/json, text/plain, */*"}


def fetch(client):
    client.get_text(WARM, headers=HEADERS)                  # 第一步：暖场拿 cookie（罐内保存）
    payload = client.get_json(API, headers=HEADERS)

    if not isinstance(payload, dict):
        raise RuntimeError("雪球响应不是 JSON")
    if payload.get("error_code"):
        raise RuntimeError(f"雪球风控拦截 error_code={payload.get('error_code')}"
                          "（需浏览器环境或代理；按规范不伪造数据）")

    rows = ((payload.get("data") or {}).get("items")) or []
    if not rows:
        raise RuntimeError("雪球 hot_stock 返回空列表（形状可能已变）")

    out: list[Item] = []
    for i, k in enumerate(rows, 1):
        if k.get("ad"):
            continue                                        # 与 newsnow 一致：过滤广告位
        name = (k.get("name") or "").strip()
        code = k.get("code")
        if not (name and code):
            continue
        pct, exch = k.get("percent"), k.get("exchange")
        out.append(Item(
            ext_id=str(code),
            title=name,
            url=f"https://xueqiu.com/s/{code}",
            rank=i,
            heat=None,                                      # 规范第 4 条
            extra={"percent": pct, "exchange": exch} if (pct is not None or exch) else None,
        ))
    return out
