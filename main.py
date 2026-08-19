"""人物卡生成器 - 主程序（CustomTkinter GUI）"""
from __future__ import annotations
import os
import json
import threading
from datetime import datetime
from typing import Dict, Any, Optional

import customtkinter as ctk
from tkinter import messagebox, filedialog

import settings_manager as sm
import quote_service as qs
import llm_client as llm
import template_generator as tg
from character_model import CharacterCard

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(BASE_DIR, "cards")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(CARDS_DIR, exist_ok=True)


def _load_roleplay_engine() -> str:
    """读取 Roleplay 引擎模板（附加到卡片末尾，启用思维链/状态栏/时间流逝/行动推荐）"""
    try:
        p = os.path.join(TEMPLATES_DIR, "roleplay_engine.txt")
        with open(p, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception as e:
        print(f"[roleplay] 模板读取失败: {e}")
        return ""

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT = ("微软雅黑", 14)
FONT_SMALL = ("微软雅黑", 12)
FONT_TITLE = ("微软雅黑", 20, "bold")
FONT_BTN = ("微软雅黑", 14, "bold")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("人物卡生成器")
        self.geometry("1100x720")
        self._center()

        self.settings = sm.load()
        self.character: Dict[str, Any] = {}
        self.last_card: Optional[CharacterCard] = None
        self.correction: str = ""
        self._gen_lock = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabs = ctk.CTkTabview(self, fg_color="#1e1e2e")
        self.tabs.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")
        self.tab_input = self.tabs.add("① 人设输入")
        self.tab_clarify = self.tabs.add("② 补齐信息")
        self.tab_result = self.tabs.add("③ 生成结果")
        self._build_input_tab(self.tab_input)
        self._build_clarify_tab(self.tab_clarify)
        self._build_result_tab(self.tab_result)
        self.tabs.set("① 人设输入")

    def _center(self):
        self.update_idletasks()
        w, h = 1100, 720
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    # ---------- Tab 1：人设输入 ----------
    def _build_input_tab(self, p):
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(p, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text="📝 输入角色设定", font=FONT_TITLE).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="⚙ 设置", width=90, font=FONT_BTN,
                      command=self.open_settings).grid(row=0, column=1, sticky="e", padx=(8, 0))

        self.input_box = ctk.CTkTextbox(p, font=FONT, height=220, wrap="word")
        self.input_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        row2.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row2, text="角色名（可留空）：", font=FONT).grid(row=0, column=0, sticky="w")
        self.name_entry = ctk.CTkEntry(row2, font=FONT)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=8)
        ctk.CTkButton(row2, text="下一步：补齐人设 →", font=FONT_BTN,
                      command=self.go_clarify).grid(row=0, column=2, padx=(8, 0))

        # 提示：动态显示 API 状态与填写规则
        has_key = bool((self.settings.get("api_key") or "").strip())
        tip_text = (
            "📋 填写规则：角色描述和角色名填一个即可（二选一），"
            "描述越具体越能减少后续提问。示例：一位孤僻的图书馆管理员，毒舌但心软，喜欢吐槽读者。"
        )
        tip = ctk.CTkLabel(
            p,
            text=tip_text,
            font=FONT_SMALL, text_color="#888", justify="left", wraplength=560,
        )
        tip.grid(row=3, column=0, sticky="w", padx=8, pady=(0, 4))

        if not has_key:
            tip_api = ctk.CTkLabel(
                p,
                text="💡 建议：到 ⚙ 设置填入 API Key（DeepSeek/Kimi/OpenAI 兼容接口），"
                     "将生成数千字的完整作者风格长卡；当前未配置，使用本地模板模式（内容较简略）。",
                font=FONT_SMALL, text_color="#c98a2d", justify="left", wraplength=560,
            )
            tip_api.grid(row=4, column=0, sticky="w", padx=8, pady=(0, 4))

    # ---------- Tab 2：补齐信息 ----------
    def _build_clarify_tab(self, p):
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(p, text="❓ 我需要确认几个关键信息", font=FONT_TITLE).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 4))

        body = ctk.CTkFrame(p, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(2, weight=1)

        self.q_label = ctk.CTkLabel(body, text="（开始）", font=FONT,
                                     wraplength=900, justify="left")
        self.q_label.grid(row=0, column=0, sticky="w", pady=(0, 8))

        # 一行完成：快捷选项 + 自由填写 + 确认 + 跳过
        input_row = ctk.CTkFrame(body, fg_color="transparent")
        input_row.grid(row=1, column=0, sticky="ew", pady=4)
        input_row.grid_columnconfigure(1, weight=1)
        self.q_combo = ctk.CTkComboBox(input_row, font=FONT, values=["请选择"], width=200)
        self.q_combo.grid(row=0, column=0, padx=(0, 8))
        self.q_entry = ctk.CTkEntry(input_row, font=FONT, placeholder_text="或自由填写…")
        self.q_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.q_entry.bind("<Return>", lambda e: self._confirm_answer())
        ctk.CTkButton(input_row, text="✅ 确认", width=90, font=FONT_BTN,
                      command=self._confirm_answer).grid(row=0, column=2, padx=(0, 8))
        ctk.CTkButton(input_row, text="跳过", width=90, font=FONT_BTN, fg_color="#555",
                      command=self._skip_field).grid(row=0, column=3)

        self.summary_box = ctk.CTkTextbox(body, font=FONT_SMALL, height=160, wrap="word")
        self.summary_box.grid(row=3, column=0, sticky="nsew", pady=(8, 4))
        self.summary_box.configure(state="disabled")

        bottom = ctk.CTkFrame(p, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=8, pady=(4, 8))
        bottom.grid_columnconfigure(0, weight=1)
        self.progress_lbl = ctk.CTkLabel(bottom, text="", font=FONT_SMALL, text_color="#888")
        self.progress_lbl.grid(row=0, column=0, sticky="w")
        ctk.CTkButton(bottom, text="← 返回修改", width=120, font=FONT_BTN, fg_color="#555",
                      command=lambda: self.tabs.set("① 人设输入")).grid(row=0, column=1, padx=(8, 0))
        self.gen_btn = ctk.CTkButton(bottom, text="⏩ 跳过剩余，直接生成", font=FONT_BTN,
                                     command=self.go_generate)
        self.gen_btn.grid(row=0, column=2, padx=(8, 0))

        self.clarify_queue: list[str] = []
        self.clarify_idx = 0

    # ---------- Tab 3：生成结果 ----------
    def _build_result_tab(self, p):
        p.grid_columnconfigure(0, weight=1)
        p.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(p, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(top, text="🎬 生成结果", font=FONT_TITLE).grid(row=0, column=0, sticky="w")
        self.status_lbl = ctk.CTkLabel(top, text="就绪", font=FONT_SMALL, text_color="#888")
        self.status_lbl.grid(row=0, column=1, sticky="e", padx=12)

        self.result_box = ctk.CTkTextbox(p, font=FONT, wrap="word")
        self.result_box.grid(row=2, column=0, sticky="nsew", padx=8, pady=4)
        self.result_box.configure(state="disabled")

        btns = ctk.CTkFrame(p, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=8, pady=(4, 8))
        btns.grid_columnconfigure(2, weight=1)
        # 次级操作靠左
        ctk.CTkButton(btns, text="🔄 重新生成", width=130, font=FONT_BTN, fg_color="#444",
                      command=self.regenerate).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(btns, text="✏ 编辑人设总结", width=130, font=FONT_BTN, fg_color="#444",
                      command=self.edit_description).grid(row=0, column=1, sticky="w", padx=(8, 0))
        ctk.CTkButton(btns, text="📋 复制全文", width=130, font=FONT_BTN, fg_color="#444",
                      command=self.copy_card).grid(row=0, column=2, sticky="w", padx=(8, 0))
        # 主操作靠右
        self.confirm_btn = ctk.CTkButton(btns, text="✅ 确认准确，保存卡片", width=200, font=FONT_BTN,
                                         command=self.ask_confirm)
        self.confirm_btn.grid(row=0, column=3, sticky="e", padx=(8, 0))
        ctk.CTkButton(btns, text="← 返回修改", width=120, font=FONT_BTN, fg_color="#555",
                      command=lambda: self.tabs.set("② 补齐信息")).grid(row=0, column=4, sticky="e", padx=(8, 0))

    # ---------- 设置对话框 ----------
    def open_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("⚙ 设置")
        win.geometry("540x480")
        win.transient(self)
        win.grab_set()
        win.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(win, text="⚙ 生成设置", font=FONT_TITLE).grid(row=0, column=0, pady=(12, 4))
        ctk.CTkLabel(
            win,
            text="填入 OpenAI 兼容接口（DeepSeek / Kimi / OpenAI 等）的 Key 即可启用 AI 生成；\n留空则自动使用本地模板模式。",
            font=FONT_SMALL, text_color="#888", justify="left",
        ).grid(row=1, column=0, sticky="w", padx=20)

        form = ctk.CTkFrame(win, fg_color="transparent")
        form.grid(row=2, column=0, sticky="nsew", padx=20, pady=8)
        form.grid_columnconfigure(1, weight=1)
        s = self.settings

        ctk.CTkLabel(form, text="API Base URL：", font=FONT).grid(row=0, column=0, sticky="w", pady=6)
        e_base = ctk.CTkEntry(form, font=FONT)
        e_base.insert(0, s.get("base_url", ""))
        e_base.grid(row=0, column=1, sticky="ew", pady=6, padx=(8, 0))

        ctk.CTkLabel(form, text="API Key：", font=FONT).grid(row=1, column=0, sticky="w", pady=6)
        e_key = ctk.CTkEntry(form, font=FONT, show="*")
        e_key.insert(0, s.get("api_key", ""))
        e_key.grid(row=1, column=1, sticky="ew", pady=6, padx=(8, 0))

        ctk.CTkLabel(form, text="模型名：", font=FONT).grid(row=2, column=0, sticky="w", pady=6)
        e_model = ctk.CTkEntry(form, font=FONT)
        e_model.insert(0, s.get("model", "deepseek-chat"))
        e_model.grid(row=2, column=1, sticky="ew", pady=6, padx=(8, 0))

        ctk.CTkLabel(form, text="联网搜索角色台词：", font=FONT).grid(row=3, column=0, sticky="w", pady=6)
        sw_search = ctk.CTkSwitch(form, text="开启", font=FONT)
        if s.get("use_web_search", True):
            sw_search.select()
        sw_search.grid(row=3, column=1, sticky="w", pady=6, padx=(8, 0))

        ctk.CTkLabel(form, text="附加 Roleplay 引擎：", font=FONT).grid(row=4, column=0, sticky="w", pady=6)
        sw_engine = ctk.CTkSwitch(form, text="开启（HUD状态栏/时间流逝/行动推荐）", font=FONT_SMALL)
        if s.get("use_roleplay_engine", False):
            sw_engine.select()
        sw_engine.grid(row=4, column=1, sticky="w", pady=6, padx=(8, 0))

        ctk.CTkLabel(form, text="卡片风格分支：", font=FONT).grid(row=5, column=0, sticky="w", pady=6)
        branches = ["通用", "恋爱养成", "宿命剧情", "CP互动"]
        cb_branch = ctk.CTkComboBox(form, values=branches, font=FONT, width=220)
        cb_branch.set(s.get("card_branch", "通用"))
        cb_branch.grid(row=5, column=1, sticky="w", pady=6, padx=(8, 0))

        def save():
            self.settings["base_url"] = e_base.get().strip() or "https://api.deepseek.com/v1"
            self.settings["api_key"] = e_key.get().strip()
            self.settings["model"] = e_model.get().strip() or "deepseek-chat"
            self.settings["use_web_search"] = bool(sw_search.get())
            self.settings["use_roleplay_engine"] = bool(sw_engine.get())
            self.settings["card_branch"] = cb_branch.get().strip() or "通用"
            sm.save(self.settings)
            win.destroy()
            messagebox.showinfo("设置", "已保存。", parent=self)

        ctk.CTkButton(win, text="💾 保存设置", font=FONT_BTN, command=save).grid(row=5, column=0, pady=12)

    # ---------- 流程：输入 → 澄清 ----------
    def _extract_name(self, raw: str) -> str:
        """从描述文本中提取角色名：优先「」/『』/【】括号，其次'名叫X/名字叫X/名为X'等句式"""
        import re as _re
        for pat in [r"[「『【]([^」』】]{1,20})",
                    r"(?:名叫|名字叫|名为|姓名|人称)\s*[「『\"]?([\u4e00-\u9fff·]{1,6}?)(?=[的的是，,。.！!？?」』]|$)"]:
            m = _re.search(pat, raw)
            if m:
                cand = m.group(1).strip()
                if cand and cand not in ("我", "他", "她", "它"):
                    return cand
        # 兜底：第一句较短（≤8字）时直接取第一句
        first = raw.splitlines()[0].strip().rstrip("，。；！？,.;!?")
        if 1 <= len(first) <= 8 and not any(c.isdigit() for c in first):
            return first
        return "未命名角色"

    def go_clarify(self):
        raw = self.input_box.get("1.0", "end").strip()
        name = self.name_entry.get().strip()
        if not raw and not name:
            messagebox.showwarning("提示", "请输入角色描述或角色名（二选一即可）。", parent=self)
            return
        if not name:
            # 从描述中提取角色名（「XX」或 《XX》 或「名叫XX」等），提取不到用未命名
            name = self._extract_name(raw)
        if not raw:
            # 只有名字：构造最小描述，作为后续澄清的上下文
            raw = f"角色名：{name}。这是一个还未完善细节的角色，请帮我补全设定。"
        self.character = tg.extract_persona(raw, name)

        # 构建待问字段队列：原文里没出现对应关键词的字段才问
        self.clarify_queue = []
        if not any(s in raw for s in tg.STYLE_TEMPLATES):
            self.clarify_queue.append("speaking_style")
            self.character["speaking_style"] = ""
        if not self.character.get("catchphrase"):
            self.clarify_queue.append("catchphrase")
        if not self.character.get("background"):
            self.clarify_queue.append("background")
        if not self.character.get("traits"):
            self.clarify_queue.append("traits")

        self.clarify_idx = 0
        self._refresh_summary()
        self.tabs.set("② 补齐信息")
        if self.clarify_queue:
            self._ask_current()
        else:
            self.q_label.configure(text="✨ 你输入的信息已经够完整啦！可以直接点「开始生成」，或继续补充细节。")
            self.q_combo.configure(values=["（无需补充）"])
            self.q_combo.set("（无需补充）")
            self.progress_lbl.configure(text="0/0 待确认 -- 可直接生成")

    def _ask_current(self):
        total = len(self.clarify_queue)
        if self.clarify_idx >= total:
            self.q_label.configure(text="✅ 所有关键信息已确认，可以开始生成。")
            self.q_combo.configure(values=["（已问完）"])
            self.q_combo.set("（已问完）")
            self.progress_lbl.configure(text=f"{total}/{total} 已确认")
            return
        field = self.clarify_queue[self.clarify_idx]
        label, opts = self._field_meta(field)
        self.q_label.configure(
            text=f"关于『{label}』我还不太确定：请选择一个，或自己填写。\n（第 {self.clarify_idx + 1}/{total} 项）")
        self.q_combo.configure(values=opts)
        self.q_combo.set(opts[0])
        self.q_entry.delete(0, "end")
        self.progress_lbl.configure(text=f"{self.clarify_idx}/{total} 已确认，剩余 {total - self.clarify_idx} 项")

    def _field_meta(self, field):
        if field == "speaking_style":
            return "说话风格", list(tg.STYLE_TEMPLATES.keys())
        if field == "catchphrase":
            return "口头禅 / 标志性台词", ["（没有口头禅）", "嗯……让我想想", "啧。", "别想太多", "一切都会好的"]
        if field == "background":
            return "背景 / 身份", ["图书馆管理员", "高中生", "退休侦探", "流浪剑客", "魔女",
                                  "上班族", "酒吧老板", "神秘旅人", "皇室成员", "AI 程序员"]
        if field == "traits":
            return "性格特质", ["孤僻", "外向", "腹黑", "傲娇", "三无", "阳光",
                               "冷静", "热血", "乐观", "精明", "懒散", "勇敢"]
        return field, ["（默认）"]

    def _confirm_answer(self):
        """确认当前答案：自由填写优先，其次快捷选项"""
        if self.clarify_idx >= len(self.clarify_queue):
            return
        val = self.q_entry.get().strip() or self.q_combo.get().strip()
        if not val or val == "请选择":
            return
        self._apply_answer(val)

    def _skip_field(self):
        if self.clarify_idx >= len(self.clarify_queue):
            return
        field = self.clarify_queue[self.clarify_idx]
        if field == "speaking_style":
            self.character["speaking_style"] = "沉稳"
        elif field == "catchphrase":
            self.character["catchphrase"] = ""
        elif field == "background":
            self.character["background"] = "来历不明"
        elif field == "traits":
            self.character["traits"] = ["沉稳"]
        self.clarify_idx += 1
        self._refresh_summary()
        self._ask_current()
        self._maybe_auto_generate()

    def _maybe_auto_generate(self):
        """关键信息全部确认完毕后，自动进入生成（无需再手动点『开始生成』）"""
        if self.clarify_queue and self.clarify_idx >= len(self.clarify_queue):
            self.after(400, self.go_generate)

    def _apply_answer(self, val):
        if self.clarify_idx >= len(self.clarify_queue):
            return
        field = self.clarify_queue[self.clarify_idx]
        if field == "speaking_style":
            for s in tg.STYLE_TEMPLATES:
                if s in val:
                    self.character["speaking_style"] = s
                    break
            else:
                self.character["speaking_style"] = "沉稳"
        elif field == "catchphrase":
            self.character["catchphrase"] = "" if val.startswith("（没有") else val
        elif field == "background":
            self.character["background"] = val
        elif field == "traits":
            self.character["traits"] = [t.strip() for t in val.replace("、", ",").split(",") if t.strip()]
        self.clarify_idx += 1
        self._refresh_summary()
        self._ask_current()
        self._maybe_auto_generate()

    def _refresh_summary(self):
        c = self.character
        lines = ["── 当前人设信息 ──",
                 f"角色名：{c.get('name') or '（待定）'}",
                 f"说话风格：{c.get('speaking_style') or '（待定）'}",
                 f"口头禅：{c.get('catchphrase') or '（无）'}",
                 f"背景：{c.get('background') or '（待定）'}",
                 f"性格特质：{'、'.join(c.get('traits')) if c.get('traits') else '（待定）'}"]
        if c.get("age_gender"):
            lines.append(f"性别/年龄：{c.get('age_gender')}")
        if c.get("dialogue_examples"):
            lines.append(f"互动示例：{len(c['dialogue_examples'])} 组（AI 会模仿其语气）")
        if c.get("interaction_rules"):
            shown = "；".join(c["interaction_rules"][:3])
            if len(c["interaction_rules"]) > 3:
                shown += "…"
            lines.append(f"互动规则：{shown}")
        self.summary_box.configure(state="normal")
        self.summary_box.delete("1.0", "end")
        self.summary_box.insert("1.0", "\n".join(lines))
        self.summary_box.configure(state="disabled")

    # ---------- 流程：澄清 → 生成 ----------
    def go_generate(self):
        if not self.character.get("name"):
            self.character["name"] = "未命名角色"
        if not self.character.get("speaking_style"):
            self.character["speaking_style"] = "沉稳"
        if not self.character.get("background"):
            self.character["background"] = "来历不明"
        if not self.character.get("traits"):
            self.character["traits"] = ["沉稳"]
        self.tabs.set("③ 生成结果")
        self._do_generate()

    def _do_generate(self):
        if self._gen_lock:
            return
        self._gen_lock = True
        self.confirm_btn.configure(state="disabled")
        self.status_lbl.configure(text="正在生成中…")
        self._set_result("⏳ 正在获取名句并生成对话，请稍候……\n")
        threading.Thread(target=self._generate_thread, daemon=True).start()

    def _generate_thread(self):
        try:
            use_api = llm.is_configured(self.settings)
            mode_tag = "AI 模式" if use_api else "本地模板模式"

            # 角色资料：真实存在的角色联网收集资料（原创角色跳过），
            # 作为台词与扩展档案的参考素材
            info: list = []
            name = (self.character.get("name") or "").strip()
            if name and name != "未命名角色" and self.settings.get("use_web_search", True):
                info = qs.search_character_info(self.character, count=4)

            # Roleplay 引擎模板（可选附加，默认关闭；开启才附加）
            rp_engine = ""
            if self.settings.get("use_roleplay_engine", False):
                rp_engine = _load_roleplay_engine()

            # ---- AI 模式：一次生成完整长卡（作者模板 v0.4：千夏/达妮娅/夏弥/多托雷风格） ----
            long_card: Dict[str, Any] = {}
            branch = self.settings.get("card_branch", "通用")
            if use_api:
                try:
                    long_card = llm.generate_full_card_json(
                        self.character, self.settings, info=info,
                        correction=self.correction, card_branch=branch)
                except Exception as e:
                    print(f"[llm full-card] 失败降级分段生成: {e}")

            if long_card.get("core_instruction"):
                # 完整长卡模式
                quotes = long_card.get("quotes") or []
                dialogues: list = []
                description = ""
                try:
                    dialogues = llm.generate_dialogue_api(self.character, self.settings, n=4)
                except Exception as e:
                    print(f"[llm dialogue] 失败降级模板: {e}")
                    dialogues = tg.generate_dialogue(self.character)
                try:
                    description = llm.generate_description_api(
                        self.character, self.settings, correction=self.correction)
                except Exception as e:
                    print(f"[llm desc] 失败降级模板: {e}")
                    description = tg.generate_description(self.character)
                if not quotes:
                    quotes = tg.generate_quotes(self.character, count=5)
                card = CharacterCard(
                    name=self.character.get("name", "未命名角色"),
                    traits=list(self.character.get("traits") or []),
                    speaking_style=self.character.get("speaking_style") or "沉稳",
                    catchphrase=self.character.get("catchphrase") or "",
                    background=self.character.get("background") or "",
                    quotes=quotes,
                    dialogues=dialogues,
                    description=description,
                    dialogue_examples=list(self.character.get("dialogue_examples") or []),
                    interaction_rules=list(self.character.get("interaction_rules") or []),
                    info=info,
                    meta=long_card.get("meta") or {},
                    core_instruction=long_card.get("core_instruction") or "",
                    output_rules=long_card.get("output_rules") or [],
                    ooc_defense=long_card.get("ooc_defense") or [],
                    basic_info=long_card.get("basic_info") or {},
                    backstory=long_card.get("backstory") or [],
                    relationships=long_card.get("relationships") or [],
                    how_referred=long_card.get("how_referred") or {},
                    language_style=long_card.get("language_style") or {},
                    classic_lines=long_card.get("classic_lines") or {},
                    likes_dislikes=long_card.get("likes_dislikes") or [],
                    core_values=long_card.get("core_values") or [],
                    self_referral=long_card.get("self_referral") or [],
                    appellation_rules=long_card.get("appellation_rules") or [],
                    affinity_system=long_card.get("affinity_system") or {},
                    affinity_dialogues=long_card.get("affinity_dialogues") or {},
                    inner_monologues=long_card.get("inner_monologues") or {},
                    physical_interactions=long_card.get("physical_interactions") or {},
                    social_relations=long_card.get("social_relations") or {},
                    communication_codes=long_card.get("communication_codes") or {},
                    scene_dialogues=long_card.get("scene_dialogues") or {},
                    story_timeline=long_card.get("story_timeline") or {},
                    extra_settings=long_card.get("extra_settings") or {},
                    roleplay_engine=rp_engine,
                )
                mode_tag = "AI 完整长卡模式"
            else:
                # ---- 降级路径：分段生成（旧逻辑） ----
                quotes: list = []
                if use_api:
                    try:
                        quotes = llm.generate_quotes_api(self.character, self.settings, n=5)
                    except Exception as e:
                        print(f"[llm quotes] 失败降级: {e}")
                if not quotes:
                    if name and name != "未命名角色":
                        quotes = qs.match_local_character_quotes(name, count=5)
                        if not quotes and self.settings.get("use_web_search", True):
                            quotes = qs.search_character_quotes(name, count=5)
                if not quotes:
                    quotes = tg.generate_quotes(self.character, count=5)

                relationships: list = []
                likes_dislikes: list = []
                core_values: list = []
                if use_api:
                    try:
                        extras = llm.generate_profile_extras(
                            self.character, self.settings, info=info)
                        relationships = extras.get("relationships") or []
                        likes_dislikes = extras.get("likes_dislikes") or []
                        core_values = extras.get("core_values") or []
                    except Exception as e:
                        print(f"[llm extras] 失败跳过: {e}")

                if use_api:
                    try:
                        dialogues = llm.generate_dialogue_api(self.character, self.settings, n=4)
                    except Exception as e:
                        print(f"[llm dialogue] 失败降级模板: {e}")
                        dialogues = tg.generate_dialogue(self.character)
                        mode_tag = "本地模板模式（AI 调用失败）"
                    try:
                        description = llm.generate_description_api(
                            self.character, self.settings, correction=self.correction)
                    except Exception as e:
                        print(f"[llm desc] 失败降级模板: {e}")
                        description = tg.generate_description(self.character)
                else:
                    dialogues = tg.generate_dialogue(self.character)
                    description = tg.generate_description(self.character)

                card = CharacterCard(
                    name=self.character.get("name", "未命名角色"),
                    traits=list(self.character.get("traits") or []),
                    speaking_style=self.character.get("speaking_style") or "沉稳",
                    catchphrase=self.character.get("catchphrase") or "",
                    background=self.character.get("background") or "",
                    quotes=quotes,
                    dialogues=dialogues,
                    description=description,
                    dialogue_examples=list(self.character.get("dialogue_examples") or []),
                    interaction_rules=list(self.character.get("interaction_rules") or []),
                    info=info,
                    relationships=relationships,
                    likes_dislikes=likes_dislikes,
                    core_values=core_values,
                    roleplay_engine=rp_engine,
                )
                # 无 Key 时用模板拼装长卡分层结构
                if not use_api:
                    card = tg.fill_long_card_fallback(card)

            self.last_card = card
            self.after(0, lambda: self._render_card(card, mode_tag))
        except Exception as e:
            self.after(0, lambda: self._gen_error(str(e)))

    def _render_card(self, card: CharacterCard, mode_tag: str):
        self._gen_lock = False
        self.status_lbl.configure(text=f"✅ 生成完成（{mode_tag}）")
        md = card.to_markdown()
        self._set_result(md + f"\n\n---\n_模式：{mode_tag}_\n")
        self.confirm_btn.configure(state="normal")

    def _gen_error(self, msg):
        self._gen_lock = False
        self.status_lbl.configure(text="❌ 生成失败")
        self._set_result(f"生成失败：{msg}\n\n可以点『重新生成』再试一次。")
        self.confirm_btn.configure(state="normal")

    def _set_result(self, text):
        self.result_box.configure(state="normal")
        self.result_box.delete("1.0", "end")
        self.result_box.insert("1.0", text)
        self.result_box.configure(state="disabled")

    def regenerate(self):
        self.correction = ""
        self._do_generate()

    def copy_card(self):
        """复制完整卡片全文到剪贴板"""
        if not self.last_card:
            return
        md = self.last_card.to_markdown()
        self.clipboard_clear()
        self.clipboard_append(md)
        self.status_lbl.configure(text="📋 已复制完整卡片到剪贴板")

    def edit_description(self):
        if not self.last_card:
            return
        win = ctk.CTkToplevel(self)
        win.title("✏ 编辑人设总结")
        win.geometry("720x440")
        win.transient(self)
        win.grab_set()
        ctk.CTkLabel(win, text="只修改卡片最底部「人设总结」这一段（不影响上方 System 指令层与角色档案层）。\n"
                               "完整卡片的其他部分如需调整，请点「重新生成」或在输入阶段补充细节。",
                     font=FONT_SMALL, text_color="#888", justify="left").pack(pady=(8, 4))
        tb = ctk.CTkTextbox(win, font=FONT, wrap="word")
        tb.pack(fill="both", expand=True, padx=12, pady=4)
        tb.insert("1.0", self.last_card.description)

        def save():
            self.last_card.description = tb.get("1.0", "end").strip()
            md = self.last_card.to_markdown()
            self._set_result(md + "\n\n---\n_（描述已手动修改）_")
            win.destroy()

        ctk.CTkButton(win, text="💾 保存修改", font=FONT_BTN, command=save).pack(pady=8)

    # ---------- 确认环节 ----------
    def ask_confirm(self):
        if not self.last_card:
            return
        card = self.last_card
        win = ctk.CTkToplevel(self)
        win.title("确认人设准确性")
        win.geometry("820x640")
        win.transient(self)
        win.grab_set()
        ctk.CTkLabel(win, text=f"角色【{card.name}】完整卡片预览（可滚动检查）：", font=FONT_TITLE).pack(pady=(12, 4))
        tb = ctk.CTkTextbox(win, font=FONT, wrap="word", height=380)
        tb.pack(fill="both", expand=True, padx=12, pady=4)
        tb.insert("1.0", card.to_markdown())
        tb.configure(state="disabled")

        btns = ctk.CTkFrame(win, fg_color="transparent")
        btns.pack(fill="x", padx=12, pady=(4, 12))

        def accurate():
            win.destroy()
            self._save_card()

        def wrong():
            win.destroy()
            self._ask_correction()

        def manual():
            win.destroy()
            self.edit_description()

        def copy():
            win.clipboard_clear()
            win.clipboard_append(card.to_markdown())
            messagebox.showinfo("复制", "✅ 完整卡片已复制到剪贴板。", parent=win)

        ctk.CTkButton(btns, text="✅ 准确，保存卡片", font=FONT_BTN,
                      command=accurate).grid(row=0, column=0, padx=4)
        ctk.CTkButton(btns, text="📋 复制完整卡片", font=FONT_BTN, fg_color="#555",
                      command=copy).grid(row=0, column=1, padx=4)
        ctk.CTkButton(btns, text="❌ 不准确，重新生成", font=FONT_BTN, fg_color="#aa3030",
                      command=wrong).grid(row=0, column=2, padx=4)
        ctk.CTkButton(btns, text="✏ 手动修改后保存", font=FONT_BTN, fg_color="#555",
                      command=manual).grid(row=0, column=3, padx=4)

    def _ask_correction(self):
        win = ctk.CTkToplevel(self)
        win.title("哪里不准确？")
        win.geometry("560x260")
        win.transient(self)
        win.grab_set()
        ctk.CTkLabel(win, text="请简述哪里不对（程序会据此重新生成）：", font=FONT).pack(pady=(12, 4))
        e = ctk.CTkEntry(win, font=FONT, width=500)
        e.pack(padx=12, pady=4, fill="x")
        e.focus_set()

        def go():
            self.correction = e.get().strip()
            win.destroy()
            self._do_generate()

        ctk.CTkButton(win, text="重新生成", font=FONT_BTN, command=go).pack(pady=8)
        e.bind("<Return>", lambda ev: go())

    def _save_card(self):
        if not self.last_card:
            return
        card = self.last_card
        safe = "".join(c for c in card.name if c.isalnum() or c in "._-") or "角色"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{safe}_{ts}.txt"
        path = filedialog.asksaveasfilename(
            title="保存人物卡",
            initialdir=CARDS_DIR,
            initialfile=default_name,
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("Markdown 文件", "*.md"), ("JSON 文件", "*.json")],
        )
        if not path:
            return  # 用户取消
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == ".json":
                content = json.dumps(card.to_dict(), ensure_ascii=False, indent=2)
            else:
                content = card.to_markdown()
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self)
            return

        messagebox.showinfo("保存成功", f"✅ 人物卡已保存：\n{path}", parent=self)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
