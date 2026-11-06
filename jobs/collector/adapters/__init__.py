#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""适配器注册表（自动发现）

规范：新增一个源 = 在本目录新增一个 `.py` 文件，暴露 SRC_ID / NAME / CATEGORY / fetch；
      **不需要改动本文件，也不需要改动 collect.py**。

排除：以 `_` 开头的文件（基类、工具）不参与发现。
"""
from __future__ import annotations

import importlib
import importlib.util
import re
import sys
import types
from pathlib import Path

from .base import Adapter, HttpClient, Item, clip, num, strip_html  # noqa: F401  （对外统一出口）

_PKG = Path(__file__).parent
_REGISTRY: dict[str, types.ModuleType] = {}
_LOADED = False


def discover(force: bool = False) -> dict[str, types.ModuleType]:
    """扫描本目录，收集所有适配器模块（模块级 SRC_ID 即注册键）。

    ⚠️ 用「按文件路径加载」而不是 `import_module`：源 id 里常有连字符或数字开头
    （如 `qq-news.py`、`36kr.py`），这些不是合法 Python 标识符，无法直接 import。
    按路径加载后可以给模块起一个合法别名，同时让 `from .base import …` 仍能工作。
    """
    global _LOADED
    if _LOADED and not force:
        return _REGISTRY
    reg: dict[str, types.ModuleType] = {}
    for path in sorted(_PKG.glob("*.py")):
        if path.name.startswith("_"):
            continue
        alias = re.sub(r"\W", "_", path.stem)
        if alias[:1].isdigit():
            alias = f"m{alias}"
        full = f"{__name__}.{alias}"
        mod = sys.modules.get(full)
        if mod is None:
            spec = importlib.util.spec_from_file_location(full, path)
            if spec is None or spec.loader is None:
                continue
            mod = importlib.util.module_from_spec(spec)
            sys.modules[full] = mod                  # 注册后再执行，保证相对导入可用
            try:
                spec.loader.exec_module(mod)
            except Exception as e:                   # noqa: BLE001 —— 单个适配器坏掉不拖垮全局
                print(f"  ⚠️ 适配器加载失败 {path.name}: {type(e).__name__}: {str(e)[:80]}")
                sys.modules.pop(full, None)
                continue
        sid = getattr(mod, "SRC_ID", None)
        if not sid or not hasattr(mod, "fetch"):
            continue                                 # 不是适配器，跳过（辅助模块）
        reg[sid] = mod
    _REGISTRY.clear()
    _REGISTRY.update(reg)
    _LOADED = True
    return _REGISTRY


def get(src_id: str):
    """按 src_id 取适配器；不存在返回 None。"""
    return discover().get(src_id)


def all_adapters() -> dict[str, object]:
    return dict(discover())


def new_client(**kw) -> HttpClient:
    return HttpClient(**kw)


def specs() -> list[dict]:
    """给 bootstrap / 文档用：列出所有适配器的元信息。"""
    out = []
    for sid, mod in sorted(discover().items()):
        out.append({"src_id": sid, "name": getattr(mod, "NAME", sid),
                    "category": getattr(mod, "CATEGORY", "其他"),
                    "module": mod.__name__})
    return out
