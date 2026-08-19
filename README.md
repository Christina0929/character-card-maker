# Character Card Maker

> **⚠️ Work in Progress** — Features and UI may change at any time. No stable release yet. Feedback is welcome.

A desktop GUI tool that turns a one-line character idea into a complete **character card**: it fills in missing persona details, generates **character lines** and **in-character dialogue**, and asks you to confirm the persona before saving.

## Features

- **Desktop GUI** — dark CustomTkinter interface, fully mouse-driven, no command line required.
- **Asks when it's not sure** — if the speaking style, catchphrase, background, or personality traits are missing, it walks you through them one by one, with dropdown options, free-form input, and a skip button.
- **Dual-mode dialogue generation**:
  - **AI mode** (with API key): calls any OpenAI-compatible model (DeepSeek / Kimi / OpenAI, etc.) to write natural, in-character dialogue and a persona summary.
  - **Local template mode** (no key): built-in dialogue templates for 8 speaking styles (sharp-tongued / gentle / aloof / chuunibyou / calm / lively / mature / airheaded) — works out of the box.
- **Character lines that they actually said**:
  - **AI mode**: the LLM recalls real lines from well-known characters; for original characters it writes lines that fit the persona.
  - **No key**: matches against the built-in quote library (`quotes/characters.json`, 25+ characters like Luffy, Conan, Sun Wukong), then tries web search, then falls back to templates.
  - **Original characters never get canned quotes** — no more "everyone says 天行健".
- **Online character research**: for real, existing characters, the app searches the web (Moegirlpedia first, Bing as fallback) and shows what it found in a dedicated "Character Info (Web)" section of the card. With an API key, the research is fed to the AI as source material.
- **Final confirmation**: after the persona summary is generated, a dialog asks whether it's accurate. If not, you can give one-line feedback and the AI regenerates with the correction in mind.
- **Export**: saves `cards/{character}_{timestamp}.md` (readable card) and `.json` (structured data).

## Installation

Requires Python 3.10+ (tested on Python 3.12).

```bash
cd character-card-maker
pip install -r requirements.txt
```

Dependencies: `customtkinter`, `requests`.

## Usage

### Step 1: Enter the persona
In the "① 人设输入" tab, describe your character in a sentence or two. For example:

> A reclusive librarian, sharp-tongued but soft-hearted, likes to mock the readers

The character name can be left blank (the app will let you set it later). Click "⚙ 设置" in the top-right to configure an API key (see below).

### Step 2: Fill in the details
Switch to the "② 补齐信息" tab. The app extracts speaking style, catchphrase, background, and traits from your description. **Fields it couldn't detect are asked one by one**:

- Each question offers a dropdown of options plus a free-form input — just pick one or type your own, then hit "✅ 确认" (Enter works too).
- A live summary of the current persona is shown on the right.
- Once the last question is answered, the app **auto-jumps to generation** — no extra button to press. The "⏩ 跳过剩余，直接生成" button is there only if you want to skip the remaining questions and generate right away.

### Step 3: Generate
In the "③ 生成结果" tab, the app:

1. Collects 5 character lines (AI mode recalls/creates them; no-key mode: built-in library → web search → templates).
2. Generates 3–5 in-character dialogues (AI in AI mode, templates otherwise).
3. Writes a persona summary.

The result is shown as a full markdown card, including sections for **character info (web research)**, **relationships**, **likes & dislikes**, and **core values** (the last three require AI mode). You can "🔄 重新生成" or "✏ 编辑描述" to adjust.

### Step 4: Confirm accuracy
Click "✅ 确认准确，保存卡片" to open the confirmation dialog with the full persona summary. Three options:

- **准确，保存卡片**: saves to the `cards/` directory and lets you open the folder.
- **不准确，重新生成**: type what's wrong; the feedback is fed back to the AI for regeneration.
- **手动修改后保存**: edit the summary text directly, then save.

## API Configuration (optional but recommended)

Click "⚙ 设置" on the main window:

| Field | Description | Example |
|-------|-------------|---------|
| API Base URL | OpenAI-compatible endpoint | `https://api.deepseek.com/v1` |
| API Key | Your key (leave blank for local template mode) | `sk-...` |
| Model | Model to call | `deepseek-chat` |
| 联网搜索角色台词 | Web search for character lines (no-key mode) | on |

Settings are stored in `settings.json`. **Leaving the API key blank still works** — dialogue and summary just fall back to local templates.

### Common endpoints

- **DeepSeek**: Base URL `https://api.deepseek.com/v1`, model `deepseek-chat`
- **Kimi (Moonshot)**: Base URL `https://api.moonshot.cn/v1`, model `moonshot-v1-8k`
- **OpenAI**: Base URL `https://api.openai.com/v1`, model `gpt-4o-mini`
- **Qwen (通义千问)**: Base URL `https://dashscope.aliyuncs.com/compatible-mode/v1`, model `qwen-turbo`

## Customizing the Quote Library

Edit `quotes/characters.json` to extend the built-in library — format is "character name → array of lines":

```json
{
  "路飞": ["我是要成为海贼王的男人！", "肉！肉！肉！"]
}
```

Both exact and substring matching are supported (e.g. "蒙奇·D·路飞" matches "路飞"). Matched characters get their **real spoken lines** — no web search, no fabrication.

## Project Structure

```
character-card-maker/
├── main.py              # Entry point + GUI main program
├── character_model.py   # Character card data model
├── settings_manager.py  # Settings persistence
├── llm_client.py        # OpenAI-compatible API client
├── quote_service.py     # Character lines & info (local library + web search)
├── template_generator.py# Local template fallback generator
├── requirements.txt     # Dependencies
├── settings.json        # Settings (created on first run)
├── quotes/              # Built-in quote library
│   └── characters.json  # character name → real lines (extendable)
└── cards/               # Saved character cards (created on first run)
```

## Technical Notes

- All network requests run on a separate thread; the UI never freezes.
- If an AI call fails, the app automatically degrades to local template mode without breaking the flow.
- Character lines are obtained via a cascade: AI mode (LLM recall/create) → built-in library → web search → templates. Original characters never get canned quotes.
- Output files: `.md` (human-readable) + `.json` (structured, for further processing).
