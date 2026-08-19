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

    def to_markdown(self) -> str:
        lines = [f"# 人物卡 · {self.name}", ""]
        lines.append("## 基本信息")
        lines.append(f"- **说话风格**：{self.speaking_style}")
        if self.catchphrase:
            lines.append(f"- **口头禅**：{self.catchphrase}")
        if self.traits:
            lines.append(f"- **性格特质**：{'、'.join(self.traits)}")
        if self.background:
            lines.append(f"- **背景**：{self.background}")
        lines.append("")
        if self.info:
            lines.append("## 角色资料（联网收集）")
            for i, x in enumerate(self.info, 1):
                lines.append(f"{i}. {x}")
            lines.append("")
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
        if self.relationships:
            lines.append("## 社交关系")
            for r in self.relationships:
                lines.append(f"- {r}")
            lines.append("")
        if self.likes_dislikes:
            lines.append("## 喜好与厌恶")
            for x in self.likes_dislikes:
                lines.append(f"- {x}")
            lines.append("")
        if self.core_values:
            lines.append("## 核心观念")
            for v in self.core_values:
                lines.append(f"- {v}")
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
        return "\n".join(lines)

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
        }
        return cls(**known)
