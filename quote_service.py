"""名句获取服务：搜索「角色亲口说过的经典台词」与「角色资料」"""
from __future__ import annotations
from typing import List, Dict, Any
import json
import os
import re
import requests

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 占位角色名：视为原创角色，不联网搜索
_PLACEHOLDER_NAMES = ("", "未命名角色", "未命名")

CHARACTERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quotes", "characters.json")

# 资料搜索时排除的无关内容特征（词典/文字/广告等）
_IRRELEVANT_KW = ("拼音", "汉字", "的意思", "千问", "AI助手", "大模型", "笔画",
                  "组词", "造句", "说文解字", "新华字典", "广告", "推广")

# HTML 实体 → 字符
_ENTITIES = {
    "&amp;": "&", "&quot;": '"', "&#x27;": "'", "&apos;": "'",
    "&lt;": "<", "&gt;": ">", "&nbsp;": " ", "&ensp;": " ", "&emsp;": " ",
    "&#0183;": "·", "&middot;": "·", "&hellip;": "…",
}


def load_character_library() -> Dict[str, List[str]]:
    """读取内置知名角色台词库（quotes/characters.json）"""
    try:
        with open(CHARACTERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): [str(x) for x in v] for k, v in data.items() if v}
    except Exception as e:
        print(f"[characters] 读取台词库失败: {e}")
    return {}


def match_local_character_quotes(character_name: str, count: int = 5) -> List[str]:
    """在内置知名角色台词库中匹配角色，返回她/他亲口说过的台词。

    支持精确匹配和包含匹配（如「蒙奇·D·路飞」可命中「路飞」）。
    未命中返回空列表。
    """
    name = (character_name or "").strip()
    if not name or name in _PLACEHOLDER_NAMES:
        return []
    lib = load_character_library()
    for key, quotes in lib.items():
        if name == key or (len(key) >= 2 and (key in name or name in key)):
            return list(quotes)[:count]
    return []


def _clean_snippet(s: str) -> str:
    """清理 Bing 搜索结果片段（去标签 + 还原 HTML 实体）"""
    clean = re.sub(r"<[^>]+>", "", s)
    for k, v in _ENTITIES.items():
        clean = clean.replace(k, v)
    return re.sub(r"\s+", " ", clean).strip()


def _extract_quotes(text: str) -> List[str]:
    """从片段中提取引号内的台词（「」/“”/""）"""
    out: List[str] = []
    for m in re.findall(r"「([^」]{2,60})」|“([^”]{2,60})”|\"([^\"]{2,60})\"", text):
        t = next((x for x in m if x), "")
        if t and t not in out:
            out.append(t)
    return out


def search_character_quotes(character_name: str, count: int = 5) -> List[str]:
    """搜索该角色亲口说过的经典台词/名场面语录（cn.bing，国内可访问）。

    仅当角色名不是占位符时调用。结果优先取片段中引号内的台词，
    其次保留明确提到角色名的介绍片段；搜不到时返回空列表，
    由调用方改用生成路径。
    """
    name = (character_name or "").strip()
    if name in _PLACEHOLDER_NAMES:
        return []

    queries = [
        f'"{name}" 经典台词',
        f'"{name}" 说过',
        f"{name} 名场面 语录",
    ]
    quoted: List[str] = []
    snippets: List[str] = []
    for q in queries:
        try:
            r = requests.get(
                "https://cn.bing.com/search",
                params={"q": q},
                headers={"User-Agent": _UA},
                timeout=12,
            )
            if r.status_code != 200:
                continue
            lis = re.findall(r'<li class="b_algo".*?</li>', r.text, re.DOTALL)
            for li in lis:
                ps = re.findall(r'<p[^>]*>(.*?)</p>', li, re.DOTALL)
                if not ps:
                    continue
                snip = _clean_snippet(ps[0])
                if name not in snip:
                    continue  # 必须提到角色名才算命中
                for t in _extract_quotes(snip):
                    if t not in quoted:
                        quoted.append(t)
                if snip not in snippets:
                    snippets.append(snip)
            if len(quoted) >= count:
                break
        except Exception as e:
            print(f"[char quotes] 搜索失败: {e}")
            continue

    # 引号台词优先；不足时用提到角色名的介绍片段补齐
    out: List[str] = []
    out.extend(quoted)
    for s in snippets:
        if len(out) >= count:
            break
        if s not in out:
            out.append(s)
    return out[:count]


def search_character_info(character_dict: Dict[str, Any], count: int = 4) -> List[str]:
    """联网搜索角色资料（简介/性格/背景），返回相关条目摘要。

    优先级：萌娘百科（opensearch 定位条目 + extracts 取导言，ACG 角色最全）
    → cn.bing 网页搜索兜底（冷门/非 ACG 专名）。
    原创角色（名字为占位符）或全部失败时返回空列表，由调用方改用生成路径。
    """
    name = (character_dict.get("name") or "").strip()
    if name in _PLACEHOLDER_NAMES:
        return []

    # 从原始人设文本提取作品名（《xxx》）
    work = ""
    m = re.search(r"《([^》]{1,20})》", character_dict.get("_raw") or "")
    if m:
        work = m.group(1).strip()

    out = _moegirl_info(name, work, count)
    if not out:
        out = _bing_info(name, work, count)
    return out[:count]


def _moegirl_info(name: str, work: str, count: int) -> List[str]:
    """萌娘百科：opensearch 搜索条目 → extracts 取导言摘要"""
    q = f"{name} {work}".strip() if work else name
    out: List[str] = []
    try:
        r = requests.get(
            "https://zh.moegirl.org.cn/api.php",
            params={"action": "opensearch", "search": q, "format": "json", "limit": "5"},
            headers={"User-Agent": _UA},
            timeout=12,
        )
        if r.status_code != 200:
            return out
        titles = r.json()[1] if isinstance(r.json(), list) and len(r.json()) > 1 else []
    except Exception as e:
        print(f"[moegirl] 搜索失败: {e}")
        return out

    for t in titles:
        if name not in t:
            continue  # 条目必须与角色名相关
        try:
            r2 = requests.get(
                "https://zh.moegirl.org.cn/api.php",
                params={"action": "query", "titles": t, "prop": "extracts",
                        "explaintext": "1", "exintro": "1", "format": "json"},
                headers={"User-Agent": _UA},
                timeout=12,
            )
            if r2.status_code != 200:
                continue
            pages = r2.json().get("query", {}).get("pages", {})
            for p in pages.values():
                ext = (p.get("extract") or "").strip()
                if ext:
                    out.append(f"{t}：{ext[:200]}")
                    break
        except Exception as e:
            print(f"[moegirl] 取简介失败: {e}")
            continue
        if len(out) >= count:
            break
    return out[:count]


def _bing_info(name: str, work: str, count: int) -> List[str]:
    """cn.bing 网页搜索兜底：片段须含角色名，过滤词典/广告等无关内容"""
    queries: List[str] = []
    if work:
        queries.append(f'"{name}" {work} 角色 介绍')
        queries.append(f'"{name}" {work} 性格 设定')
    queries.append(f'"{name}" 角色 性格 背景')

    out: List[str] = []
    for q in queries:
        try:
            r = requests.get(
                "https://cn.bing.com/search",
                params={"q": q},
                headers={"User-Agent": _UA},
                timeout=12,
            )
            if r.status_code != 200:
                continue
            lis = re.findall(r'<li class="b_algo".*?</li>', r.text, re.DOTALL)
            for li in lis:
                ps = re.findall(r'<p[^>]*>(.*?)</p>', li, re.DOTALL)
                if not ps:
                    continue
                snip = _clean_snippet(ps[0])
                if name not in snip:
                    continue  # 必须提到角色名
                if any(k in snip for k in _IRRELEVANT_KW):
                    continue  # 过滤词典/广告等无关内容
                if snip not in out:
                    out.append(snip[:180])
                if len(out) >= count:
                    break
            if len(out) >= count:
                break
        except Exception as e:
            print(f"[char info] 搜索失败: {e}")
            continue
    return out[:count]