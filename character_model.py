"""人物卡数据模型"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import List


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
        if self.dialogues:
            lines.append("## 人设对话")
            for i, d in enumerate(self.dialogues, 1):
                lines.append(f"{i}. {d}")
            lines.append("")
        if self.quotes:
            lines.append("## 收集名句")
            for i, q in enumerate(self.quotes, 1):
                lines.append(f"{i}. {q}")
            lines.append("")
        if self.description:
            lines.append("## 人设总结")
            lines.append(self.description)
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
        }
        return cls(**known)
