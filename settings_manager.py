"""设置持久化：JSON 文件读写"""
from __future__ import annotations
import json
import os
from typing import Any, Dict

SETTINGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

DEFAULTS: Dict[str, Any] = {
    "api_key": "",
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "use_web_search": True,
    "quote_category": "k",
}


def load() -> Dict[str, Any]:
    """加载设置，缺失/损坏时返回默认值"""
    if not os.path.exists(SETTINGS_PATH):
        return dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        merged = dict(DEFAULTS)
        merged.update(data)
        return merged
    except Exception as e:
        print(f"[settings] 读取失败，使用默认值: {e}")
        return dict(DEFAULTS)


def save(settings: Dict[str, Any]) -> None:
    """保存设置到 settings.json"""
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[settings] 保存失败: {e}")
