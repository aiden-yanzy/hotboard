#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""原神 · 官方公告（米游社 gids=2）

移植自 DailyHotApi（imsyy/DailyHotApi，MIT License）routes/genshin.ts
共用逻辑见 `_miyoushe.py`。heat 恒为 None（上游的 view_status 是状态位，不是热度）。
"""
from __future__ import annotations

from ._miyoushe import fetch_news

SRC_ID = "genshin"
NAME = "原神公告"
CATEGORY = "娱乐"

URL_PREFIX = "https://www.miyoushe.com/ys/article/"


def fetch(client):
    return fetch_news(client, gids=2, url_prefix=URL_PREFIX)
