"""名句获取服务：一言 API + 搜索引擎兜底 + 本地文件"""
from __future__ import annotations
from typing import Dict, Any, List
import os
import glob
import re
import requests

QUOTES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quotes")

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 一言 API 分类映射
HITOKOTO_CATEGORIES: Dict[str, str] = {
    "k": "哲学/名言",
    "i": "诗词",
    "d": "文学",
    "h": "影视",
    "a": "动画",
    "b": "漫画",
    "c": "游戏",
    "j": "网易云",
    "e": "原创",
    "f": "网络",
    "g": "其他",
}


def fetch_hitokoto(category: str = "k", count: int = 5) -> List[str]:
    """从一言 API 获取名句"""
    results: List[str] = []
    seen = set()
    for _ in range(count + 3):
        try:
            r = requests.get(
                "https://v1.hitokoto.cn/",
                params={"encode": "json", "c": category},
                timeout=8,
                headers={"User-Agent": _UA},
            )
            if r.status_code != 200:
                continue
            d = r.json()
            hito = (d.get("hitokoto") or "").strip()
            if not hito or hito in seen:
                continue
            seen.add(hito)
            frm = (d.get("from") or "").strip()
            who = (d.get("from_who") or "").strip()
            seg = f"「{hito}」"
            if frm:
                seg += f"--《{frm}》"
            if who:
                seg += f" {who}"
            results.append(seg)
            if len(results) >= count:
                break
        except Exception as e:
            print(f"[hitokoto] 失败: {e}")
            continue
    return results


def search_quotes(keyword: str, count: int = 5) -> List[str]:
    """用 DuckDuckGo HTML 搜索名句（兜底）"""
    if not keyword:
        return []
    try:
        r = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": f"{keyword} 名言 名句 经典台词"},
            headers={"User-Agent": _UA},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        text = r.text
        snippets = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', text, re.DOTALL)
        out: List[str] = []
        for s in snippets:
            clean = re.sub(r"<[^>]+>", "", s).strip()
            clean = (clean.replace("&amp;", "&").replace("&quot;", '"')
                     .replace("&#x27;", "'").replace("&lt;", "<").replace("&gt;", ">"))
            if 5 < len(clean) < 200:
                out.append(clean)
            if len(out) >= count:
                break
        return out
    except Exception as e:
        print(f"[search] 失败: {e}")
        return []


def load_local_quotes() -> List[str]:
    """读取 quotes/ 目录下所有 .txt 文件中的名句"""
    out: List[str] = []
    for path in sorted(glob.glob(os.path.join(QUOTES_DIR, "*.txt"))):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        out.append(line)
        except Exception as e:
            print(f"[local] 读取 {path} 失败: {e}")
    return out


def get_quotes_for_character(character_dict: Dict[str, Any], settings: Dict[str, Any], count: int = 5) -> List[str]:
    """为角色获取名句：联网优先，失败降级本地"""
    quotes: List[str] = []
    use_web = settings.get("use_web_search", True)
    cat = settings.get("quote_category", "k") or "k"

    if use_web:
        try:
            quotes.extend(fetch_hitokoto(category=cat, count=count))
        except Exception:
            pass
        if len(quotes) < count:
            kw = (character_dict.get("catchphrase") or character_dict.get("speaking_style")
                  or character_dict.get("name") or "")
            if kw:
                quotes.extend(search_quotes(kw, count=max(0, count - len(quotes))))

    if len(quotes) < count:
        local = load_local_quotes()
        for q in local:
            if q not in quotes:
                quotes.append(q)
            if len(quotes) >= count:
                break

    # 不足时复用补齐
    if quotes:
        i = 0
        while len(quotes) < count:
            quotes.append(quotes[i % len(quotes)])
            i += 1
    return quotes[:count]
