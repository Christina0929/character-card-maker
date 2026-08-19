# Character Card Maker (人物卡生成器)

> A desktop GUI tool that turns a one-line character idea into a complete, ready-to-feed **character card** for roleplay AI / agent persona swapping.

把一句话人设变成可直接喂给 AI 做角色扮演 / agent 换皮的**完整分层角色卡**。模仿抖音角色卡作者「夏夜雨绵y」（千夏/达妮娅/夏弥/多托雷）的卡面结构。

## Features

### 🎴 Author-style long card (v0.4+)
Generates a structured, layered card modeled on the popular Douyin character-card author's style:

- **System instruction layer** — core instruction, self-referral rules, address rules, output constraints, OOC defense
- **Character profile layer** — background story, language style, classic lines, social relations, likes & dislikes, core values
- **Affinity system (好感度)** — 5-level affinity ladder, dialogue tables per level, inner-monologue library, physical-interaction feedback
- **Relationship / story layers** — social-relation table, communication codes, scene dialogue scripts, story timeline

### 🎭 Three style branches (卡片风格分支)
| Branch | Focus |
|--------|-------|
| 通用 (General) | Balanced default |
| 恋爱养成 (Romance/Raising) | Affinity 5-level system + dialogue table + inner monologues + physical interactions |
| 宿命剧情 (Fated Story) | Relationship five-piece set + theme deepening + meta language style |
| CP互动 (CP Interaction) | Communication-code mechanism + scene script library + story timeline + tri-state language style |

### 🤖 Dual-mode generation
- **AI mode** (with API key): calls any OpenAI-compatible model (DeepSeek / Kimi / OpenAI / Qwen…) to write a full 23-key long card (up to 8000 tokens), tuned per branch.
- **Local template mode** (no key): **background-aware** templates — 12 profession-specific dialogue pools (librarian / teacher / student / doctor / detective / hacker / swordsman / witch / assassin / merchant / chef / reporter), auto-detected from the description, plus 8 speaking-style pools.

### 🧩 Smart input
- **Name & description are either-or** — fill in one. If you only give a description, the name is auto-extracted (`「名字」`, `名叫X`, `名字叫X` …).
- **Guided clarification** — missing fields are asked one by one (dropdown + free input + skip).
- Real characters get their **actual spoken lines** (AI recall → built-in quote library → web search → templates), original characters never get canned quotes.

### 🎨 Polished dark UI
- **霞鹜文楷 (LXGW WenKai)** bundled font — loaded privately via GDI, auto-fallback to 微软雅黑
- Warm-gold dark theme, one-click launcher on desktop

## Screenshots

*(coming soon)*

## Installation

Requires **Python 3.10+** (tested on 3.12). Windows recommended (font loading uses GDI).

```bash
cd character-card-maker
pip install -r requirements.txt
```

Dependencies: `customtkinter`, `requests`.

## Usage

### Quick start

**Double-click `启动人物卡生成器.bat`** (or the desktop shortcut「人物卡生成器」) — starts with `pythonw.exe`, no console window.

### Step 1 — Enter the persona

In the "① 人设输入" tab, describe the character. Either field is enough:

- **角色描述** — e.g. `一位孤僻的图书馆管理员，毒舌但心软，喜欢吐槽读者`
- **角色名** — optional; auto-extracted from the description if blank

> 💡 Without an API key, a hint suggests configuring one — AI mode produces far richer cards.

### Step 2 — Fill in the details

The "② 补齐信息" tab asks for anything the description didn't cover (speaking style, catchphrase, background, traits…), one field at a time with dropdown options, free-form input, or skip.

### Step 3 — Generate

In "③ 生成结果", the app builds the full long card. From here you can:

- **🔄 重新生成** — regenerate
- **✏ 编辑人设总结** — edit only the persona-summary paragraph (bottom section)
- **📋 复制全文** — copy the complete markdown card to clipboard
- **✅ 确认准确，保存卡片** — opens a full-card preview dialog; then **save as** `.txt` / `.md` / `.json` anywhere, or copy the full card

### Step 4 — Save / share

The saved `.md` card is the final deliverable — paste it into any roleplay AI or agent persona.

## API Configuration (optional but recommended)

Click "⚙ 设置" on the main window:

| Field | Description | Example |
|-------|-------------|---------|
| API Base URL | OpenAI-compatible endpoint | `https://api.deepseek.com/v1` |
| API Key | Your key (leave blank for local template mode) | `sk-...` |
| Model | Model to call | `deepseek-chat` |
| 联网搜索角色台词 | Web search for character lines | on |
| 附加 Roleplay 引擎 | Appends a HUD/status-panel engine template (**off by default**) | off |
| 卡片风格分支 | 通用 / 恋爱养成 / 宿命剧情 / CP互动 | 通用 |

Settings are stored in `settings.json` (git-ignored — **your API key never gets committed**).

### Common endpoints

| Provider | Base URL | Model |
|----------|----------|-------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| Kimi (Moonshot) | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| Qwen (通义千问) | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-turbo` |

## Customizing the Quote Library

Edit `quotes/characters.json` — format is "character name → array of lines":

```json
{
  "路飞": ["我是要成为海贼王的男人！", "肉！肉！肉！"]
}
```

Both exact and substring matching are supported. Matched characters get their **real spoken lines**.

## Project Structure

```
character-card-maker/
├── main.py                 # Entry point + GUI main program
├── character_model.py      # Character card data model (23-key structure)
├── llm_client.py           # OpenAI-compatible API client (branch-aware prompts)
├── template_generator.py   # Local template fallback (background-aware pools)
├── quote_service.py        # Character lines & info (local library + web search)
├── settings_manager.py     # Settings persistence
├── 启动人物卡生成器.bat     # One-click launcher (pythonw, no console)
├── requirements.txt        # Dependencies
├── fonts/                  # Bundled 霞鹜文楷 (LXGW WenKai) fonts
├── quotes/                 # Built-in quote library
│   └── characters.json
├── templates/              # Roleplay engine template (optional add-on)
├── cards/                  # Saved character cards (auto-created)
└── settings.json           # Local settings — git-ignored (API key stays private)
```

## Technical Notes

- All network requests run on a separate thread; the UI never freezes.
- AI call failure automatically degrades to local template mode.
- Font loading: `AddFontResourceEx` (private, per-process) → family detection → fallback to 微软雅黑.
- Character lines cascade: AI mode → built-in library → web search → templates. Original characters never get canned quotes.
- Card export: `.txt` / `.md` (human-readable markdown) + `.json` (structured data).

## Roadmap

- [x] v0.3 — Long-card structure + Roleplay engine add-on
- [x] v0.4 — Author-style 23-key card + 3 style branches
- [x] v0.4.1 — Save-as dialog, copy full card, name/description either-or
- [x] v0.4.5 — Background-aware local templates (12 profession pools)
- [x] v0.4.6 — 霞鹜文楷 font + warm-gold dark theme
- [x] v0.4.7 — One-click desktop launcher