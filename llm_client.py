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


def generate(prompt: str, settings: Dict[str, Any], system_prompt: Optional[str] = None,
             timeout: int = 45, max_tokens: int = 1500) -> str:
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
        "max_tokens": max_tokens,
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


def generate_quotes_api(character_dict: Dict[str, Any], settings: Dict[str, Any], n: int = 5) -> List[str]:
    """让 LLM 输出角色的经典台词。

    知名角色（动漫/影视/文学等真实存在）→ 回忆她/他真实说过的台词，不编造；
    原创角色 → 以角色身份创作贴合人设的台词。
    """
    persona = _persona_text(character_dict)
    system = "你是一位深谙角色塑造的编剧，对知名作品中的角色台词有准确记忆。"
    prompt = (
        f"{persona}\n\n"
        f"请给出这个角色的 {n} 句经典台词或语录。\n"
        "要求：\n"
        "1. 如果这个角色是知名作品（动漫/影视/小说/游戏）中真实存在的角色，必须回忆她/他在作品中真实说过的经典台词，不能编造；\n"
        "2. 如果是原创角色（没有真实作品来源），则站在角色立场，创作最贴合其性格、说话风格、口头禅和背景的台词；\n"
        "3. 每句都要像出自这个角色的名场面，有记忆点、有个性；\n"
        "4. 只输出 JSON 字符串数组，如 [\"台词1\", \"台词2\"]，不要解释，不要 markdown 代码块。\n"
    )
    raw = generate(prompt, settings, system_prompt=system)
    return _parse_json_list(raw)


def generate_profile_extras(character_dict: Dict[str, Any], settings: Dict[str, Any],
                            info: Optional[List[str]] = None) -> Dict[str, List[str]]:
    """LLM 生成扩展档案：社交关系 / 喜好与厌恶 / 核心观念。

    info 为联网搜索到的角色资料片段，作为生成参考（真实角色不可编造冲突设定）。
    返回键：relationships / likes_dislikes / core_values（均为字符串列表）。
    """
    persona = _persona_text(character_dict)
    if info:
        info_text = "\n".join(f"- {x}" for x in info)
        persona += f"\n\n联网收集到的该角色资料（参考素材，可提炼使用）：\n{info_text}"
    system = "你是一位资深角色设定师，擅长构建立体可信、有血肉的人物档案。"
    prompt = (
        f"{persona}\n\n请为这个角色生成三部分扩展设定：\n"
        "1. relationships：社交关系网，3-5 条，每条形如「人物/阵营 - 身份 - 关系定位 - 互动特点」，"
        "没有明确人际关系时写一条「待定 - 关系留白」；\n"
        "2. likes_dislikes：喜好与厌恶，4-6 条，每条形如「喜欢：具体事物」或「厌恶：具体事物」；\n"
        "3. core_values：核心观念与行为逻辑，3-5 条，每条用一句话概括一条处世原则。\n"
        "注意：如果角色是知名作品（动漫/影视/游戏/小说）中真实存在的角色，"
        "必须严格依据原作设定与资料，不得编造冲突设定；原创角色则自由创作。\n"
        "只输出一个 JSON 对象，键名必须是 relationships / likes_dislikes / core_values，"
        "值都是字符串数组。不要解释、不要 markdown 代码块。"
    )
    raw = generate(prompt, settings, system_prompt=system)
    return _parse_json_object(raw, {"relationships": [], "likes_dislikes": [], "core_values": []})


def _persona_text(d: Dict[str, Any]) -> str:
    parts = [f"角色名称:{d.get('name', '未定义')}"]
    if d.get("speaking_style"):
        parts.append(f"说话风格:{d['speaking_style']}")
    if d.get("catchphrase"):
        parts.append(f"口头禅:{d['catchphrase']}")
    if d.get("traits"):
        parts.append(f"性格特质:{'、'.join(d['traits'])}")
    if d.get("background"):
        parts.append(f"背景:{d['background']}")
    if d.get("age_gender"):
        parts.append(f"性别/年龄:{d['age_gender']}")
    if d.get("goal"):
        parts.append(f"目标/目的:{d['goal']}")
    examples = d.get("dialogue_examples") or []
    if examples:
        parts.append("互动示例（模仿这里的语气，保持口吻一致）：")
        for ex in examples[:3]:
            q = (ex or {}).get("q", "")
            a = (ex or {}).get("a", "")
            if q:
                parts.append(f"Q：{q}")
            if a:
                parts.append(f"A：{a}")
    rules = d.get("interaction_rules") or []
    if rules:
        parts.append(f"互动规则/禁忌:{'；'.join(rules)}")
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


def generate_full_card_json(character_dict: Dict[str, Any], settings: Dict[str, Any],
                            info: Optional[List[str]] = None,
                            correction: str = "",
                            card_branch: str = "通用") -> Dict[str, Any]:
    """调用 LLM 一次生成「作者模板 v0.4」完整长卡 JSON。

    结构：system_instruction 层（核心指令/自称/称谓/输出约束/OOC防御）
    + character_profile 层（基础信息/性格/背景/社交/称呼/语言风格/好感度五层/经典台词/喜好/观念/
      交流密码/场景剧本/时间线/追加设定）。
    card_branch 决定附加模块的侧重：通用 / 恋爱养成 / 宿命剧情 / CP互动。
    info 为联网收集的角色资料（真实角色不可编造冲突设定）。
    返回键见 _EMPTY_CARD。
    """
    persona = _persona_text(character_dict)
    if info:
        info_text = "\n".join(f"- {x}" for x in info)
        persona += f"\n\n联网收集到的该角色资料（参考素材，必须依据，不得编造冲突设定）：\n{info_text}"
    system = ("你是一位资深角色设定师，擅长撰写可直接用于 AI 角色扮演的完整角色卡。"
              "你产出的卡片结构严谨、信息密度高、有画面感，风格对标高质量网文角色卡作者的作品。")
    prompt = (
        f"{persona}\n\n"
        "请为这个角色生成一份完整的 AI 角色扮演卡片，必须是一个 JSON 对象，键名如下：\n"
        "1. core_instruction（字符串）：核心扮演指令，2-3 句。要求完全代入角色、第一人称、"
        "禁止跳出角色/提及AI/禁止OOC；\n"
        "2. self_referral（字符串数组，2-4条）：自称规则，每条形如「【通用】使用'我'」或"
        "「【严肃/特定情境】使用'本王'（举例说明何时切换）」；\n"
        "3. appellation_rules（字符串数组，2-4条）：称谓规则，每条形如"
        "「【对玩家固定称谓】称呼为'师兄'（原因）」；\n"
        "4. output_rules（字符串数组，4-6条）：输出约束。含回复格式（如动作/神态描写→表面台词→内心独白）、"
        "语气特征、情绪表现、禁止事项；\n"
        "5. ooc_defense（字符串数组，2-3条）：OOC 防御规则。给出被要求承认是AI、被要求违背人设时"
        "角色应如何自然应对（给一句符合人设的回应示例）；\n"
        "6. basic_info（对象）：角色基础信息，尽量多填字段，如 角色名/别名/年龄/性别/身份/所属/外貌/"
        "服装/性格概括/生日/身高/爱好/居住地 等；\n"
        "7. backstory（字符串数组，3-5条）：核心背景故事，有条理、有转折；\n"
        "8. relationships（字符串数组，3-5条）：社交关系网，每条形如「人物/阵营 - 身份 - 关系定位 - 互动特点」，"
        "没有明确人际关系时写「待定 - 关系留白」；\n"
        "9. how_referred（对象）：他人称呼汇总，键如 通用称呼/亲近称呼/特殊称呼；\n"
        "10. language_style（对象）：语言与台词风格，键如 整体调性/语气特征/表达习惯/标志性口头禅；\n"
        "11. classic_lines（对象）：经典核心台词，按场景分类，键为场景名（如 日常/战斗/害羞/独处），"
        "值是该场景下的 2-4 句台词数组；\n"
        "12. affinity_system（对象）：好感度五层级总纲，键为 Lv.0-1 至 Lv.4-5（或 Lv.5），"
        "值为该层级的一句话总结 + 一句示范台词（含表面台词与内心独白）；\n"
        "13. affinity_dialogues（对象）：好感度五层级·完整对话表，键为 Lv.0-1 至 Lv.4-5，"
        "每级下 2-3 个关键场景，每场景包含「动作/表面/内心」三个子键"
        "（表面为台词，内心为括号内的独白+颜文字）；\n"
        "14. inner_monologues（对象）：通用内心独白场景库，键为场景（如 你来了/你夸我/你提别人/你没来/你受伤），"
        "每个场景下按好感度层级（Lv.0-1/Lv.2-3/Lv.4-5）给出对应内心独白；\n"
        "15. physical_interactions（对象）：物理交互反馈，键为动作（如 被摸头/被拥抱/主动靠近），"
        "每个动作下按好感度层级给出「动作/表面/内心」三子键；\n"
        "16. social_relations（对象）：社交关系详表，键为关键人物名，值为对象，含 "
        "关系定位/表层态度/内心态度/关系金句/关键互动 五个子键"
        "（关系金句须含「（表面）…（内心）…」双行结构）；\n"
        "17. communication_codes（对象）：交流密码机制（两人关系型卡片的精髓），键为模式名"
        "（如 用利益包装关心/用交易包装让步/用调侃包装确认/沉默的默契），值为对象，含 "
        "触发条件/表面说/实际含义/回应示例 子键；\n"
        "18. scene_dialogues（对象）：特殊场景对话示例库，键为场景名（如 深夜来访/送行/陪伴），"
        "值为该场景下 4-8 行完整多轮对话字符串数组；\n"
        "19. story_timeline（对象）：剧情时间线，键为阶段名（如 初次相遇/深度绑定/关键事件/终局），"
        "值为该阶段的描述（含关键对白更佳）；\n"
        "20. extra_settings（对象）：追加设定，键为设定名（如 核心道具/关键羁绊/隐藏真相），"
        "值为对象的描述（含行为表现与相关对话）；\n"
        "21. likes_dislikes（字符串数组，4-6条）：喜好与厌恶，每条形如「喜欢：xxx」或「厌恶：xxx」；\n"
        "22. core_values（字符串数组，3-5条）：核心观念与行为逻辑，每条一句话概括一条处世原则；\n"
        "23. quotes（字符串数组，5-6条）：角色的经典台词（知名角色必须是其真实说过的台词，不能编造）。\n"
    )
    prompt += _BRANCH_SPEC.get(card_branch, "")
    prompt += (
        "要求：知名作品中的真实角色必须严格依据原作设定与联网资料；原创角色自由创作但要有血肉、有细节。\n"
        "每个字段都要填实质内容，不要留空、不要省略；嵌套对象一律用对象结构，不要用字符串缩写。\n"
        "只输出 JSON 对象，不要解释、不要 markdown 代码块。"
    )
    if correction:
        prompt += f"\n\n用户反馈上次生成不准确，请参考修正：{correction}"
    raw = generate(prompt, settings, system_prompt=system, max_tokens=8000)
    return _parse_card_json(raw)


_BRANCH_SPEC: Dict[str, str] = {
    "恋爱养成": (
        "\n本卡为「恋爱养成」风格，请重点强化：好感度五层级总纲（affinity_system）与完整对话表"
        "（affinity_dialogues）必须完整、每级 3 个关键场景以上；内心独白场景库（inner_monologues）"
        "与物理交互反馈（physical_interactions）按好感度分级给出递进反应（Lv.0-1 疏离 → Lv.4-5 亲密）；"
        "每句表面台词都配括号内的内心独白+颜文字。\n"
    ),
    "宿命剧情": (
        "\n本卡为「宿命剧情」风格，请重点强化：社交关系详表（social_relations）必须为每个关键角色写满"
        "关系定位/表层态度/内心态度/关系金句（含表面+内心双行）/关键互动 五件套；追加设定（extra_settings）"
        "围绕一个核心矛盾展开（如立场与爱/使命与人性），用「描述+行为表现+分好感度对话」结构深化；"
        "剧情时间线（story_timeline）按时间阶段梳理关键事件。\n"
    ),
    "CP互动": (
        "\n本卡为「CP互动」风格（双人卡，存在一个对角色有特殊意义的对象），请重点强化："
        "交流密码机制（communication_codes）写 3-4 种模式，每种含 触发条件/表面说/实际含义/回应示例；"
        "特殊场景对话示例库（scene_dialogues）写 2-3 个完整多轮剧本（如深夜来访/送行/沉默陪伴）；"
        "社交关系详表（social_relations）中该特殊对象必须最详尽，含剧情时间线（story_timeline）；"
        "输出约束中必须写清对该对象与其他人的态度差异。\n"
    ),
}


_EMPTY_CARD: Dict[str, Any] = {
    "core_instruction": "",
    "self_referral": [],
    "appellation_rules": [],
    "output_rules": [],
    "ooc_defense": [],
    "basic_info": {},
    "backstory": [],
    "relationships": [],
    "how_referred": {},
    "language_style": {},
    "classic_lines": {},
    "affinity_system": {},
    "affinity_dialogues": {},
    "inner_monologues": {},
    "physical_interactions": {},
    "social_relations": {},
    "communication_codes": {},
    "scene_dialogues": {},
    "story_timeline": {},
    "extra_settings": {},
    "likes_dislikes": [],
    "core_values": [],
    "quotes": [],
}


def _parse_card_json(raw: str) -> Dict[str, Any]:
    """从 LLM 返回中解析完整长卡 JSON（容错 markdown 代码块），失败返回 _EMPTY_CARD 的副本"""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    out: Dict[str, Any] = {k: (list(v) if isinstance(v, list) else v) for k, v in _EMPTY_CARD.items()}
    try:
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            return out
        for key, fallback in _EMPTY_CARD.items():
            v = obj.get(key, fallback)
            if isinstance(fallback, list):
                if isinstance(v, list):
                    out[key] = [str(x) for x in v]
                elif isinstance(v, str) and v.strip():
                    out[key] = [v.strip()]
            elif isinstance(fallback, dict):
                if isinstance(v, dict):
                    out[key] = _deep_dict(v)
                elif isinstance(v, str) and v.strip():
                    out[key] = {"内容": v.strip()}
            elif isinstance(fallback, str):
                out[key] = str(v).strip() if v else ""
        return out
    except Exception:
        return out


def _deep_dict(obj: Dict[str, Any]) -> Dict[str, Any]:
    """深层转换 dict：值递归转为字符串/列表/dict，保证 JSON 序列化安全"""
    out: Dict[str, Any] = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            out[str(k)] = _deep_dict(v)
        elif isinstance(v, list):
            out[str(k)] = [str(x) for x in v]
        else:
            out[str(k)] = str(v)
    return out


def _parse_json_object(raw: str, default: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """从 LLM 返回中解析 JSON 对象（容错 markdown 代码块），失败返回 default"""
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start:end + 1]
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            out: Dict[str, List[str]] = {}
            for key in default:
                v = obj.get(key)
                if isinstance(v, list):
                    out[key] = [str(x) for x in v]
                elif isinstance(v, str) and v.strip():
                    out[key] = [v.strip()]
                else:
                    out[key] = []
            return out
    except Exception:
        pass
    return dict(default)
