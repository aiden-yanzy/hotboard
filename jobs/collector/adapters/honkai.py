#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""崩坏3 · 官方公告（米游社 gids=1）

移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）routes/honkai.ts
共用逻辑见 `_miyoushe.py`。heat 恒为 None（上游的 view_status 是状态位，不是热度）。
"""
from __future__ import annotations

from ._miyoushe import fetch_news

SRC_ID = "honkai"
NAME = "崩坏3公告"
CATEGORY = "娱乐"

URL_PREFIX = "https://www.miyoushe.com/bh3/article/"


def fetch(client):
    return fetch_news(client, gids=1, url_prefix=URL_PREFIX)
