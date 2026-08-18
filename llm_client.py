"""OpenAI 兼容 Chat Completions 客户端"""
from __future__ import annotations
from typing import Dict, Any, Optional, List
import json
import re
import requests


class LLMError(Exception):
    """LLM 调用错误（中文消息）"""


def is_configured(settings: Dict[str, Any]) -> bool:
    return bool(settings.get("api_key", "").strip()) and bool(settings.get("base_url", "").strip())


def generate(prompt: str, settings: Dict[str, Any], system_prompt: Optional[str] = None, timeout: int = 45) -> str:
    """调用 chat completions 接口，返回文本"""
    api_key = settings.get("api_key", "").strip()
    base_url = settings.get("base_url", "").strip().rstrip("/")
    model = settings.get("model", "deepseek-chat").strip()
    if not api_key:
        raise LLMError("未配置 API Key，请在「设置」里填写。")
    if not base_url:
        raise LLMError("未配置 API Base URL。")

    messages: List[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 1500,
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    except requests.exceptions.Timeout:
        raise LLMError("请求超时，请检查网络或稍后重试。")
    except requests.exceptions.ConnectionError as e:
        raise LLMError(f"网络连接失败：{e}")
    except requests.exceptions.RequestException as e:
        raise LLMError(f"请求异常：{e}")

    if resp.status_code != 200:
        raise LLMError(f"接口返回错误 {resp.status_code}：{resp.text[:200]}")

    try:
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, ValueError) as e:
        raise LLMError(f"解析返回结果失败：{e}")


def generate_dialogue_api(character_dict: Dict[str, Any], settings: Dict[str, Any], n: int = 4) -> List[str]:
    """调用 LLM 生成符合人设的对话列表"""
    persona = _persona_text(character_dict)
    system = "你是一位资深角色编剧。请根据给定人设，产出符合该角色语气的口语化台词。"
    prompt = (
        f"{persona}\n\n请为这个角色生成 {n} 句符合人设的对话台词。要求：\n"
        "1. 口语化、带情绪，符合角色的说话风格与口头禅；\n"
        "2. 每句独立成行，可以是独白或对白；\n"
        "3. 只输出 JSON 数组，例如 [\"台词1\", \"台词2\"]，不要解释、不要 markdown 代码块。\n"
    )
    raw = generate(prompt, settings, system_prompt=system)
    return _parse_json_list(raw)


def generate_description_api(character_dict: Dict[str, Any], settings: Dict[str, Any], correction: str = "") -> str:
    """调用 LLM 生成人设总结描述"""
    persona = _persona_text(character_dict)
    system = "你是一位角色设定顾问，擅长用流畅的中文撰写立体的人物小传。"
    prompt = (
        f"{persona}\n\n请用 3-6 句流畅的中文，为这个角色写一段人设总结，"
        "涵盖性格内核、说话方式、典型行为和内在矛盾，要有画面感和代入感。"
        "直接输出总结正文，不要标题、不要列表。"
    )
    if correction:
        prompt += f"\n\n用户反馈上次总结不准确，请参考修正：{correction}"
    raw = generate(prompt, settings, system_prompt=system)
    return raw.strip()


def _persona_text(d: Dict[str, Any]) -> str:
    parts = [f"角色名：{d.get('name', '未命名')}"]
    if d.get("speaking_style"):
        parts.append(f"说话风格：{d['speaking_style']}")
    if d.get("catchphrase"):
        parts.append(f"口头禅：{d['catchphrase']}")
    if d.get("traits"):
        parts.append(f"性格特质：{'、'.join(d['traits'])}")
    if d.get("background"):
        parts.append(f"背景：{d['background']}")
    if d.get("age_gender"):
        parts.append(f"性别/年龄：{d['age_gender']}")
    if d.get("goal"):
        parts.append(f"立场/目标：{d['goal']}")
    return "\n".join(parts)


def _parse_json_list(raw: str) -> List[str]:
    """从 LLM 返回中解析出字符串列表，容错 markdown 代码块"""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    try:
        arr = json.loads(raw)
        if isinstance(arr, list):
            return [str(x) for x in arr][:10]
    except Exception:
        pass
    # 兜底：按行拆分
    lines = [l.strip().lstrip("0123456789.-、）) ").strip() for l in raw.splitlines() if l.strip()]
    return lines[:10]
