# Instructions

## Installation

1. Download from https://github.com/mime-r/Dungeon.py/archive/main.zip
2. Unzip and move the folder to your desired location
3. Keep all files in the folder together

### Python

Requires **Python 3.10+** (tested on 3.11 and 3.14).

Download from https://www.python.org/downloads/

During installation, make sure to:
- Check **"Add Python to PATH"**
- Ensure **pip** is included

### Dependencies

Dungeon.py only needs `rich` and `tinydb`. The launcher will offer to install them
on first run, or you can install them manually:

```
pip install -r requirements.txt
```

## Running the Game

Open the **Run** folder inside the game directory and run the appropriate script:

| Script | Platform |
| --- | --- |
| `command_prompt.bat` | Windows Command Prompt |
| `python.bat` | Python launcher |
| `windows_terminal.bat` | Windows Terminal (recommended) |
| `linux_terminal.sh` | Linux terminal |

For `windows_terminal.bat`, install Windows Terminal from the
[Microsoft Store](https://www.microsoft.com/en-us/p/windows-terminal/9n0dx20hk701).

### Step-by-step

1. **Open** the `Dungeon.py` folder (the one containing `requirements.txt`)
2. **Open** the `Run` subfolder
3. **Double-click** the script for your platform:
   - **Windows:** `windows_terminal.bat` (recommended), `command_prompt.bat`, or `python.bat`
   - **Linux:** `linux_terminal.sh` (right-click → Run as Program, or `bash linux_terminal.sh` from terminal)
4. On first run, the launcher will ask if you want to install dependencies - type `y` and press Enter
5. The game starts - choose your class and begin your descent!

### Running from a terminal directly

```
python Dungeon/__init__.py
```

Run this from the root `Dungeon.py` directory.

## LLM Configuration (Optional)

Dungeon.py includes optional AI features (biome themes, ambient flavour text, item lore,
NPC dialogue). These are **completely optional** - the game runs fine without any LLM setup.

To enable AI features, copy `.env.example` to `.env` in the game's root folder and
configure your preferred provider:

```
cp .env.example .env
```

### Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `LLM_PROVIDER` | Yes (if using AI) | Which provider to use: `lm_studio`, `openai`, or `opencode_zen` |
| `LM_STUDIO_URL` | For LM Studio | Base URL of your local LM Studio server (default `http://127.0.0.1:1234`) |
| `LM_STUDIO_API_KEY` | For LM Studio | API key for LM Studio (default `lm-studio`) |
| `LM_STUDIO_MODEL` | For LM Studio | Model name to use (e.g. `local-model`) |
| `OPENAI_API_KEY` | For OpenAI | Your OpenAI API key |
| `OPENAI_MODEL` | For OpenAI | OpenAI model to use (default `gpt-4o-mini`) |
| `OPENCODE_ZEN_URL` | For OpenCode Zen | Base URL for OpenCode Zen API |
| `OPENCODE_ZEN_API_KEY` | For OpenCode Zen | API key for OpenCode Zen |
| `OPENCODE_ZEN_MODEL` | For OpenCode Zen | OpenCode Zen model name |

### Provider Setup

**LM Studio (local, free)**
1. Download and install [LM Studio](https://lmstudio.ai/)
2. Load a model (e.g., `nvidia/nemotron-3-nano-4b`)
3. Start the local server (default port 1234)
4. Set `LLM_PROVIDER=lm_studio` in `.env`

**OpenAI**
1. Get an API key from [platform.openai.com](https://platform.openai.com/)
2. Set `LLM_PROVIDER=openai` and `OPENAI_API_KEY=sk-...` in `.env`

**OpenCode Zen**
1. Get API credentials from your OpenCode Zen provider
2. Set `LLM_PROVIDER=opencode_zen` and the corresponding URL/key/model in `.env`

### How it works

On startup, the game probes your LLM provider to confirm it's reachable. If the
connection fails or no `.env` file is present, all AI features are silently skipped - you
won't see any errors, the game just generates biomes and flavour text procedurally instead.
