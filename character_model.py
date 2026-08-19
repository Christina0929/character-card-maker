"""人物卡数据模型"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List, Dict


@dataclass
class CharacterCard:
    name: str = "未命名角色"
    traits: List[str] = field(default_factory=list)
    speaking_style: str = "沉稳"
    catchphrase: str = ""
    background: str = ""
    quotes: List[str] = field(default_factory=list)
    dialogues: List[str] = field(default_factory=list)
    description: str = ""
    dialogue_examples: List[Dict] = field(default_factory=list)
    interaction_rules: List[str] = field(default_factory=list)
    info: List[str] = field(default_factory=list)                 # 联网搜索到的角色资料
    relationships: List[str] = field(default_factory=list)        # 社交关系网（AI 生成）
    likes_dislikes: List[str] = field(default_factory=list)       # 喜好与厌恶（AI 生成）
    core_values: List[str] = field(default_factory=list)          # 核心观念（AI 生成）
    # ---- 千夏/达妮娅风格长卡字段 ----
    meta: Dict = field(default_factory=dict)                      # meta 生效规则
    core_instruction: str = ""                                    # 核心扮演指令
    output_rules: List[str] = field(default_factory=list)         # 输出约束
    ooc_defense: List[str] = field(default_factory=list)          # OOC 防御规则
    basic_info: Dict = field(default_factory=dict)                # 角色基础信息
    backstory: List[str] = field(default_factory=list)            # 核心背景故事
    how_referred: Dict = field(default_factory=dict)              # 他人称呼汇总
    language_style: Dict = field(default_factory=dict)            # 语言与台词风格
    classic_lines: Dict = field(default_factory=dict)             # 经典核心台词（按场景分类）
    roleplay_engine: str = ""                                     # Roleplay 引擎模板（可选附加）

    def to_markdown(self) -> str:
        lines = [f"# 人物卡 · {self.name}", ""]

        # ── System 指令层 ──
        if self.core_instruction or self.output_rules or self.ooc_defense:
            lines.append("## System 指令层")
            if self.core_instruction:
                lines.append("### 核心指令")
                lines.append(self.core_instruction)
                lines.append("")
            if self.output_rules:
                lines.append("### 输出约束")
                for r in self.output_rules:
                    lines.append(f"- {r}")
                lines.append("")
            if self.ooc_defense:
                lines.append("### OOC 防御规则")
                for r in self.ooc_defense:
                    lines.append(f"- {r}")
                lines.append("")

        # ── 角色档案层 ──
        has_profile = any([self.basic_info, self.traits, self.backstory, self.relationships,
                           self.how_referred, self.language_style, self.classic_lines,
                           self.likes_dislikes, self.core_values])
        if has_profile:
            lines.append("## 角色档案")
            lines.append("")
            if self.basic_info:
                lines.append("### 角色基础信息")
                for k, v in self.basic_info.items():
                    if isinstance(v, list):
                        lines.append(f"- **{k}**：{'、'.join(str(x) for x in v)}")
                    else:
                        lines.append(f"- **{k}**：{v}")
                lines.append("")
            elif self.speaking_style or self.catchphrase or self.background:
                lines.append("### 角色基础信息")
                lines.append(f"- **说话风格**：{self.speaking_style}")
                if self.catchphrase:
                    lines.append(f"- **口头禅**：{self.catchphrase}")
                if self.background:
                    lines.append(f"- **背景**：{self.background}")
                lines.append("")
            if self.traits:
                lines.append("### 核心性格特质")
                for t in self.traits:
                    lines.append(f"- {t}")
                lines.append("")
            if self.backstory:
                lines.append("### 核心背景故事")
                for i, b in enumerate(self.backstory, 1):
                    lines.append(f"{i}. {b}")
                lines.append("")
            if self.relationships:
                lines.append("### 社交关系网")
                for r in self.relationships:
                    lines.append(f"- {r}")
                lines.append("")
            if self.how_referred:
                lines.append("### 他人称呼汇总")
                for k, v in self.how_referred.items():
                    lines.append(f"- **{k}**：{v}")
                lines.append("")
            if self.language_style:
                lines.append("### 语言与台词风格")
                for k, v in self.language_style.items():
                    lines.append(f"- **{k}**：{v}")
                lines.append("")
            if self.classic_lines:
                lines.append("### 经典核心台词")
                for scene, arr in self.classic_lines.items():
                    lines.append(f"**{scene}**")
                    if isinstance(arr, list):
                        for q in arr:
                            lines.append(f"- {q}")
                    else:
                        lines.append(f"- {arr}")
                lines.append("")
            if self.likes_dislikes:
                lines.append("### 喜好与厌恶")
                for x in self.likes_dislikes:
                    lines.append(f"- {x}")
                lines.append("")
            if self.core_values:
                lines.append("### 核心观念与行为逻辑")
                for v in self.core_values:
                    lines.append(f"- {v}")
                lines.append("")

        # ── 旧版块（兼容保留）──
        if not self.basic_info and (self.speaking_style or self.catchphrase or self.background):
            pass  # 已在上方基础信息输出
        if self.dialogues:
            lines.append("## 人设对话")
            for i, d in enumerate(self.dialogues, 1):
                lines.append(f"{i}. {d}")
            lines.append("")
        if self.quotes:
            lines.append("## 角色台词")
            for i, q in enumerate(self.quotes, 1):
                lines.append(f"{i}. {q}")
            lines.append("")
        if self.description:
            lines.append("## 人设总结")
            lines.append(self.description)
            lines.append("")
        if self.info:
            lines.append("## 角色资料（联网收集）")
            for i, x in enumerate(self.info, 1):
                lines.append(f"{i}. {x}")
            lines.append("")
        if self.dialogue_examples:
            lines.append("## 互动示例")
            for ex in self.dialogue_examples:
                q = (ex or {}).get("q", "")
                a = (ex or {}).get("a", "")
                if q:
                    lines.append(f"- Q：{q}")
                if a:
                    lines.append(f"  A：{a}")
            lines.append("")
        if self.interaction_rules:
            lines.append("## 互动规则")
            for r in self.interaction_rules:
                lines.append(f"- {r}")
            lines.append("")
        if self.roleplay_engine:
            lines.append(self.roleplay_engine.strip())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CharacterCard":
        known = {
            "name": d.get("name", "未命名角色"),
            "traits": list(d.get("traits") or []),
            "speaking_style": d.get("speaking_style") or "沉稳",
            "catchphrase": d.get("catchphrase") or "",
            "background": d.get("background") or "",
            "quotes": list(d.get("quotes") or []),
            "dialogues": list(d.get("dialogues") or []),
            "description": d.get("description") or "",
            "dialogue_examples": list(d.get("dialogue_examples") or []),
            "interaction_rules": list(d.get("interaction_rules") or []),
            "info": list(d.get("info") or []),
            "relationships": list(d.get("relationships") or []),
            "likes_dislikes": list(d.get("likes_dislikes") or []),
            "core_values": list(d.get("core_values") or []),
            "meta": dict(d.get("meta") or {}),
            "core_instruction": d.get("core_instruction") or "",
            "output_rules": list(d.get("output_rules") or []),
            "ooc_defense": list(d.get("ooc_defense") or []),
            "basic_info": dict(d.get("basic_info") or {}),
            "backstory": list(d.get("backstory") or []),
            "how_referred": dict(d.get("how_referred") or {}),
            "language_style": dict(d.get("language_style") or {}),
            "classic_lines": dict(d.get("classic_lines") or {}),
            "roleplay_engine": d.get("roleplay_engine") or "",
        }
        return cls(**known)
