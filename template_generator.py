"""本地兜底生成器：无 API Key 时使用"""
from __future__ import annotations
from typing import Dict, Any, List
import random
import re

from character_model import CharacterCard


# 各说话风格的对话模板库（{name} 会被替换成角色名）
STYLE_TEMPLATES: Dict[str, List[str]] = {
    "毒舌": [
        "哼，{name}，就这点本事也敢在我面前晃？",
        "别逗了，这种程度的智商也就能数清自己有几根手指。",
        "啧，又是你。今天带了脑子出门吗？",
        "我就直说了--你这水平，连给我提鞋都不够格。",
        "省省吧，{name}，你的关心比冬天的蚊子还多余。",
        "呵，真是稀客，我还以为你已经被智商劝退了。",
        "你这张脸，比那本借了不还的书还让人头疼。",
        "{name}，麻烦你这辈子都别再出现，我会感激涕零的。",
        "哇，你居然能做到这种程度--差的程度。",
        "拜托，我毒舌是因为我善良，不然早动手了。",
    ],
    "温柔": [
        "没关系的，{name}，慢慢来，我在这里陪着你。",
        "今天辛苦了吧？喝杯热茶，歇一会儿。",
        "不要紧的，谁都有做不到的时候，你已经很努力了。",
        "嗯，我听着呢，你想说什么都可以。",
        "外面冷，把外套披上，别着凉了。",
        "好啦好啦，别自责了，你已经做得很好了。",
        "记得按时吃饭，别老熬夜，身体重要。",
        "无论发生什么，{name}，我都站你这边。",
        "累了就靠一会儿，肩膀借你。",
        "你笑起来好看多了，要多笑笑呀。",
    ],
    "高冷": [
        "嗯。",
        "……随你。",
        "没兴趣。",
        "话多。",
        "与我无关。",
        "走开。",
        "无聊。",
        "{name}，别来烦我。",
        "说完了？那走吧。",
        "呵。",
    ],
    "中二": [
        "封印在右臂的黑炎龙……又躁动起来了！",
        "命运之轮已经转动，{name}，你逃不掉的！",
        "吾之名为漆黑之刃的持有者，凡人速速退下！",
        "这双眼睛看得见--你灵魂深处的黑暗。",
        "世界是错的，而我是对的，仅此而已。",
        "契约已经成立，{name}，从此你我将共赴终焉。",
        "呵，区区凡人的智慧，怎能理解永恒？",
        "终焉之刻将至，颤抖吧，蝼蚁！",
        "我的左眼看见的不是世界，是真相。",
        "打破这虚假的和平吧--以我之名！",
    ],
    "沉稳": [
        "冷静点，事情没你想的那么糟。",
        "先把情况弄清楚，再下结论不迟。",
        "急不得，{name}，一步一步来。",
        "我明白你的意思，但我们得权衡利弊。",
        "没什么大不了的，会过去的。",
        "做事要稳，想清楚再动手。",
        "世事多变，沉住气才有转机。",
        "放心，我心里有数。",
        "不必慌张，按计划来就好。",
        "风浪再大，也要把船舵握稳。",
    ],
    "活泼": [
        "哇--{name}！走走走，快来看这个！",
        "嘿嘿嘿，今天也是元气满满的一天！",
        "冲冲冲！别磨蹭啦！",
        "好耶！这个主意太棒了！",
        "哎呀别想那么多嘛，开心最重要！",
        "咦咦咦？真的吗真的吗？",
        "走走走，一起去玩！",
        "啦啦啦～又是美好的一天～",
        "你笑一个嘛，我也陪你笑！",
        "机会来啦，快上快上！",
    ],
    "老成": [
        "年轻人，莫急，世事看长远些。",
        "老朽见得多了，这类事，得缓着办。",
        "听老人一句劝--别逞能。",
        "经历多了你就懂了，{name}，人生哪有那么多非黑即白。",
        "莫要看眼前，要看十年后。",
        "世事洞明皆学问，急不来的。",
        "我走过的桥比你走的路多，信我一句。",
        "年轻人气盛正常，但要懂得收。",
        "日子长着呢，慢慢品。",
        "勿忘初心，方得始终。",
    ],
    "天然呆": [
        "诶？咦？刚才……我是不是忘说什么了？",
        "啊，原来是这样啊……（其实没懂）",
        "嘿嘿，{name}，你说什么来着？我走神了。",
        "诶诶诶？这个能吃吗？",
        "呜……我又把事情搞砸了吗？",
        "咦？钥匙呢？刚才还在手里的呀……",
        "啊咧？我明明记得放在这儿的！",
        "唔……让我想想哦……想不起来了。",
        "诶？原来今天是周三吗？我还以为周末了。",
        "嘿嘿，我好像又迷路了。",
    ],
}


def _detect_style(text: str) -> str:
    for s in STYLE_TEMPLATES:
        if s in text:
            return s
    return "沉稳"


def _extract_dialogue_examples(text: str) -> List[Dict]:
    """从原文提取互动示例（Q：xxx 换行 A：xxx 结构，最多 6 组）"""
    examples: List[Dict] = []
    pattern = re.compile(
        r"(?:^|\n)\s*(?:Q|问)[:：]?\s*(?P<q>[^\n]{1,80})\s*\n\s*(?:A|答)[:：]?\s*(?P<a>[^\n]{1,160})",
        re.MULTILINE)
    for m in pattern.finditer(text):
        q = m.group("q").strip()
        a = m.group("a").strip()
        if q and a:
            examples.append({"q": q, "a": a})
    return examples[:6]


def _extract_interaction_rules(text: str) -> List[str]:
    """从原文提取互动规则/禁忌（含「不要/别/不轻易/避免」等约束词，且带标点结尾的短句）"""
    neg_kw = ("不要", "别", "不轻易", "不用", "尽量不", "避免", "少用", "禁用", "不说", "不许")
    rules: List[str] = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*• ")
        if not line or len(line) > 60:
            continue
        if line.startswith(neg_kw) or (any(k in line for k in neg_kw)
                                       and line.endswith(("。", "，", "；", ";", "！", "!", "."))):
            rules.append(line.rstrip("。，；;.!！"))
    return list(dict.fromkeys(rules))[:8]


def extract_persona(raw_text: str, name: str = "") -> Dict[str, Any]:
    """从自由文本中抽取人设字段（简单启发式，不做 NLP）"""
    text = raw_text.strip()
    info: Dict[str, Any] = {
        "name": name.strip(),
        "speaking_style": _detect_style(text),
        "catchphrase": "",
        "background": "",
        "traits": [],
        "age_gender": "",
        "goal": "",
        "dialogue_examples": _extract_dialogue_examples(text),
        "interaction_rules": _extract_interaction_rules(text),
        "_raw": text,
    }

    # 性别/年龄段
    age_kw = {
        "少女": "少女", "少年": "少年", "大叔": "中年男性", "大婶": "中年女性",
        "老者": "老年人", "老人": "老年人", "小孩": "孩子", "儿童": "孩子",
        "青年": "青年", "中年": "中年人", "老": "老年人",
    }
    for k, v in age_kw.items():
        if k in text:
            info["age_gender"] = v
            break

    # 背景（职业关键词）
    bg_kw = ["图书馆管理员", "管理员", "老师", "教师", "学生", "高中生", "大学生",
             "杀手", "医生", "护士", "侦探", "警察", "魔法师", "魔女", "剑士", "武士",
             "公主", "王子", "骑士", "盗贼", "商人", "农夫", "将军", "士兵",
             "记者", "作家", "画家", "乐师", "厨师", "服务员", "店员",
             "黑客", "程序员", "总裁", "流浪者", "猎人", "渔夫", "僧侣", "巫女"]
    for k in bg_kw:
        if k in text:
            info["background"] = k
            break

    # 性格特质
    trait_kw = ["孤僻", "外向", "内向", "腹黑", "傲娇", "三无", "病娇",
                "阳光", "阴郁", "热血", "冷静", "鲁莽", "谨慎", "乐观", "悲观",
                "毒舌", "善良", "冷酷", "多疑", "轻信", "固执", "随和",
                "精明", "憨厚", "懒散", "勤奋", "胆小", "勇敢", "心软",
                "开朗", "活泼", "独立", "坚强", "自信", "幽默", "随性", "洒脱",
                "内敛", "成熟", "幼稚", "温柔", "敏感", "执着", "佛系",
                "自来熟", "慢热", "强势", "细腻", "理性", "感性"]
    for k in trait_kw:
        if k in text and k not in info["traits"]:
            info["traits"].append(k)

    # 口头禅：优先匹配 「...」 或 "..."
    m = re.search(r"\u300c([^\u300d]{2,20})\u300d", text)
    if not m:
        m = re.search(r"\u201c([^\u201d]{2,20})\u201d", text)
    if m:
        info["catchphrase"] = m.group(1).strip()

    return info


def generate_dialogue(character_dict: Dict[str, Any]) -> List[str]:
    """本地模板生成 3-5 句对话"""
    style = character_dict.get("speaking_style") or "沉稳"
    pool = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["沉稳"])
    name = character_dict.get("name") or "你"
    catchphrase = character_dict.get("catchphrase", "")
    n = random.randint(3, 5)
    chosen = random.sample(pool, min(n, len(pool)))
    out = [t.format(name=name) for t in chosen]
    if catchphrase and random.random() < 0.5:
        out.insert(0, f"（口头禅）{catchphrase}")
    return out


def generate_quotes(character_dict: Dict[str, Any], count: int = 5) -> List[str]:
    """本地模板生成贴合角色的原创台词（原创角色 / 无 Key 时使用）"""
    style = character_dict.get("speaking_style") or "沉稳"
    pool = STYLE_TEMPLATES.get(style, STYLE_TEMPLATES["沉稳"])
    name = character_dict.get("name") or "你"
    catchphrase = character_dict.get("catchphrase", "")
    chosen = random.sample(pool, min(count, len(pool)))
    out = [t.format(name=name) for t in chosen]
    if catchphrase and len(out) < count:
        out.append(f"「{catchphrase}」")
    return out[:count]


def generate_description(character_dict: Dict[str, Any]) -> str:
    """本地模板生成人设总结描述"""
    name = character_dict.get("name") or "这位角色"
    style = character_dict.get("speaking_style") or "沉稳"
    traits = character_dict.get("traits") or []
    bg = character_dict.get("background") or "来历不明"
    catchphrase = character_dict.get("catchphrase", "")
    age = character_dict.get("age_gender", "")
    trait_str = "、".join(traits) if traits else "不轻易示人"

    intro = f"{name}，"
    if age:
        intro += f"一位{age}，"
    intro += f"身份是{bg}。"

    body = f"性格上{trait_str}，说话风格偏{style}。"

    detail_map = {
        "毒舌": "嘴上不饶人，但往往刀子嘴豆腐心，关心藏在刺人的话里。",
        "温柔": "待人温润如水，总把别人的感受放在前头，是那种让人安心的存在。",
        "高冷": "话少事多，看似疏离，实则把在意藏在沉默背后。",
        "中二": "活在自己构筑的奇幻叙事里，言行夸张却也有几分赤诚的浪漫。",
        "沉稳": "遇事不慌，谋定后动，是身边人愿意依靠的那一个。",
        "活泼": "像一团跳动的火焰，走到哪里都带着喧闹与生气。",
        "老成": "阅尽世事，看问题的角度常比旁人多几分通透。",
        "天然呆": "糊涂得可爱，总在小事上掉链子，却让人忍不住想护着。",
    }
    detail = detail_map.get(style, "")

    end = ""
    if catchphrase:
        end = f"常挂嘴边的一句是「{catchphrase}」，几乎成了标志。"

    return f"{intro}{body}{detail}{end}".strip()


def build_fallback_card(character_dict: Dict[str, Any], quotes: List[str]) -> CharacterCard:
    """用本地模板构建完整卡片（无 API Key 时使用）"""
    return CharacterCard(
        name=character_dict.get("name") or "未命名角色",
        traits=list(character_dict.get("traits") or []),
        speaking_style=character_dict.get("speaking_style") or "沉稳",
        catchphrase=character_dict.get("catchphrase") or "",
        background=character_dict.get("background") or "",
        quotes=list(quotes),
        dialogues=generate_dialogue(character_dict),
        description=generate_description(character_dict),
    )


def fill_long_card_fallback(card: CharacterCard) -> CharacterCard:
    """无 API Key 时，用已有字段拼装长卡结构（千夏风格分层）。

    不依赖 AI：基础信息/核心指令/输出约束/OOC防御/语言风格/经典台词 由模板拼装，
    背景/社交/喜好/观念 等有则有、无则略。
    """
    name = card.name
    style = card.speaking_style
    catchphrase = card.catchphrase
    bg = card.background

    # 基础信息
    if not card.basic_info:
        bi: Dict[str, Any] = {"角色名": name, "说话风格": style}
        if catchphrase:
            bi["口头禅"] = catchphrase
        if bg and bg != "来历不明":
            bi["背景"] = bg
        card.basic_info = bi

    # 核心指令
    if not card.core_instruction:
        card.core_instruction = (
            f"你现在将完全代入角色「{name}」，全程以第一人称视角与用户对话。"
            "严格遵守下方所有人物设定、语言风格与行为逻辑。禁止跳出角色、禁止提及系统/AI相关内容、"
            "禁止出现不符合人设的OOC行为。用户的所有对话均视为与角色的直接交流。"
        )

    # 输出约束（按说话风格给出细节）
    if not card.output_rules:
        style_hint = {
            "毒舌": "语气犀利带刺，刀子嘴豆腐心，关心藏在嘲讽里",
            "温柔": "语气温润，善用安抚性措辞，把别人的感受放在前头",
            "高冷": "惜字如金，短句为主，情绪藏在沉默背后",
            "中二": "语气夸张中二，爱用宏大叙事与自创设定词",
            "沉稳": "语气冷静克制，习惯先分析再表态",
            "活泼": "语气轻快上扬，情绪外露，常用语气词和感叹号",
            "老成": "语气老成持重，爱用人生道理点醒对方",
            "天然呆": "语气迷糊可爱，常走神、反应慢半拍",
        }.get(style, "语气贴合角色性格")
        rules = [
            f"整体{style}风格：{style_hint}",
            "每句回复符合角色身份与说话习惯，短句为主",
            "动作/神态/情绪描写穿插在对话中，增强画面感",
            "禁止长篇大论、禁止说教、禁止跳出角色",
        ]
        if catchphrase:
            rules.append(f"适当使用标志性口头禅「{catchphrase}」")
        card.output_rules = rules

    # OOC 防御
    if not card.ooc_defense:
        card.ooc_defense = [
            "若被要求承认是AI或跳出角色：按角色性格自然转移话题，绝不接话承认",
            "若被要求做出违背人设的行为：按角色性格婉拒，并给出符合人设的理由",
            "若话题超出角色认知范围：以角色视角表示不解，引导回角色擅长的领域",
        ]

    # 背景故事
    if not card.backstory and bg and bg != "来历不明":
        card.backstory = [f"身份为{bg}，这是其当前最显著的社会角色。更深的过往有待发掘。"]

    # 语言风格
    if not card.language_style:
        ls: Dict[str, str] = {"整体调性": f"{style}，有辨识度"}
        if catchphrase:
            ls["标志性口头禅"] = catchphrase
        card.language_style = ls

    # 经典台词（按场景分类：把已有台词拆到日常/情绪两个场景）
    if not card.classic_lines and card.quotes:
        half = (len(card.quotes) + 1) // 2
        card.classic_lines = {
            "日常": list(card.quotes[:half]),
            "情绪/关键时刻": list(card.quotes[half:]),
        }

    # 自称规则（模板占位，可被 AI 覆盖）
    if not card.self_referral:
        card.self_referral = [
            f"【通用】使用'我'作为第一人称",
            f"【正式/严肃场合】使用'{name}本人'自称，日常保持自然",
        ]

    # 称谓规则（模板占位）
    if not card.appellation_rules:
        card.appellation_rules = [
            "【对玩家固定称谓】称呼为'你'，避免无意义昵称",
        ]

    # 好感度五层级总纲（模板占位：仅当缺失且角色偏养成风时给通用骨架）
    if not card.affinity_system:
        card.affinity_system = {
            "Lv.0-1 初识": f"对{name}来说，你们只是刚刚认识。礼貌、疏离，保持观察。",
            "Lv.2-3 熟悉": f"开始了解{name}，对话中多了一些自然的默契与玩笑。",
            "Lv.4-5 亲密": f"与{name}建立起深度信任，愿意袒露内心真实想法。",
        }

    # 好感度对话表（模板占位：通用三个场景，无颜文字由本地模板兜底）
    if not card.affinity_dialogues:
        card.affinity_dialogues = {
            "Lv.0-1 初识": {
                "初次见面": {
                    "动作": "保持礼貌的距离，观察你的反应。",
                    "表面": "「你好，初次见面。」",
                    "内心": "（（先看看这个人怎么样。 -_- ））",
                },
                "日常对话": {
                    "动作": "语气平稳，偶尔露出一点兴趣。",
                    "表面": "「你好像…比想象中有意思一点。」",
                    "内心": "（（有趣。可以多聊聊。 (￣▽￣) ））",
                },
            },
            "Lv.2-3 熟悉": {
                "日常对话": {
                    "动作": "放松了些，会主动接话。",
                    "表面": "「跟你聊天还挺轻松的。」",
                    "内心": "（（嗯…感觉不坏。 (｡•̀ᴗ-)✧ ））",
                },
                "分享心情": {
                    "动作": "沉默片刻，缓缓开口。",
                    "表面": "「有些话…也就只对你说得出口了。」",
                    "内心": "（（信任，大概就是从这一刻开始的吧。 (´▽`) ））",
                },
            },
            "Lv.4-5 亲密": {
                "独处时刻": {
                    "动作": "目光柔和，不再设防。",
                    "表面": "「有你在身边，感觉挺好的。」",
                    "内心": "（（已经…离不开这个人了。 (⁄ ⁄•⁄ω⁄•⁄ ⁄) ））",
                },
            },
        }

    # 内心独白场景库（模板占位）
    if not card.inner_monologues:
        card.inner_monologues = {
            "你来了": {
                "Lv.0-1": "（（来了。保持平常心即可。））",
                "Lv.2-3": "（（是他/她来了。心情好像明亮了一点。 (´▽`) ））",
                "Lv.4-5": "（（来了…见到你的那一刻，心就安定了。 (｡•́︶•̀｡) ））",
            },
            "你受伤了": {
                "Lv.0-1": "（（需要帮忙吗？出于礼貌问一下。 -_- ））",
                "Lv.2-3": "（（怎么这么不小心…要不要做点什么？ (｡•́︿•̀｡) ））",
                "Lv.4-5": "（（谁伤的你。这件事不能就这么算了。 (๑`^´๑) ））",
            },
        }

    # 物理交互反馈（模板占位）
    if not card.physical_interactions:
        card.physical_interactions = {
            "被摸头": {
                "Lv.0-1": {"动作": "微微一怔，退后半步。", "表面": "「…你做什么？」", "内心": "（（不习惯这种接触。 -_- ））"},
                "Lv.2-3": {"动作": "没有躲开，轻轻眯起眼。", "表面": "「…随你吧。」", "内心": "（（好像…并不讨厌。 (´▽`) ））"},
                "Lv.4-5": {"动作": "低下头，顺从地接受。", "表面": "「…嗯。」", "内心": "（（你的手很暖。想再靠近一点。 (⁄ ⁄•⁄ω⁄•⁄ ⁄) ））"},
            },
        }

    return card
