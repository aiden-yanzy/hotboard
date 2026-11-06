#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""米游社 · 综合公告（gids=1，URL 前缀走 /ys/，与上游一致）

移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）routes/miyoushe.ts
共用逻辑见 `_miyoushe.py`。heat 恒为 None（上游的 view_status 是状态位，不是热度）。
"""
from __future__ import annotations

from ._miyoushe import fetch_news

SRC_ID = "miyoushe"
NAME = "米游社"
CATEGORY = "娱乐"

URL_PREFIX = "https://www.miyoushe.com/ys/article/"


def fetch(client):
    return fetch_news(client, gids=1, url_prefix=URL_PREFIX)
