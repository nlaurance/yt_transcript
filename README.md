# yt-transcript

YouTube audio → clean, structured Obsidian Markdown via Mistral.

Takes a YouTube URL, downloads the audio, transcribes it with Mistral Voxtral,
removes filler words and repetitions, generates a technical documentation block,
tags the content, and writes an Obsidian-ready `.md` file.

Supports French and English presentations.

## Output

Each run produces `output/<video-slug>.md` with:

- **YAML frontmatter** — title, date, source URL, presenter name, language, duration, tags
- **Cleaned transcript** — structured under `##` headings, filler words and repetitions removed
- **`## Documentation Technique`** — glossary table, architecture summary, risks & trade-offs
- Optionally: English translation of the documentation block (`--translate-summary`)
- Optionally: re-narrated MP3 (`--tts`)

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) — `brew install ffmpeg`
- A [Mistral API key](https://console.mistral.ai/api-keys)

## Setup

```bash
cp .env.example .env
# Edit .env and set MISTRAL_API_KEY=...

uv sync --group pipeline
```

## Usage

The default language is **French**. Pass `--lang en` for English talks, or `--lang auto`
to let Voxtral detect the language itself.

```bash
# French presentation — default, no flag needed
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX"

# English presentation
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" --lang en

# French talk, also write a re-narrated MP3
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" --tts

# French talk, append an English translation of the technical docs block
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" --translate-summary

# Save output to your Obsidian vault directly
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" \
  --output-dir ~/notes/talks

# English talk with all options
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" \
  --lang en \
  --tts \
  --tts-voice benjamin \
  --output-dir ~/notes/talks
```

### Options

| Flag                  | Default    | Description                                              |
|-----------------------|------------|----------------------------------------------------------|
| `--lang`              | `fr`       | Source language: `fr`, `en`, or `auto`                   |
| `--tts`               | off        | Generate a re-narrated MP3 from the processed transcript |
| `--translate-summary` | off        | Append English translation of the technical docs block   |
| `--tts-voice`         | `sasha`    | TTS voice: `sasha` (female) or `benjamin` (male)         |
| `--output-dir`        | `./output` | Directory for output files                               |

## Pipeline

```
YouTube URL
    │
    ▼  yt-dlp + ffmpeg
MP3 audio
    │
    ▼  Mistral Voxtral (STT)
Raw transcript
    │
    ├──► presenter.py   → speaker name (metadata → LLM fallback)
    │
    ▼  Mistral Small (LLM)
Cleaned Markdown + Documentation block
    │
    ├──► tagger.py      → content tags
    ├──► [--translate-summary] → EN docs block appended
    │
    ▼  frontmatter.py
Obsidian .md (YAML frontmatter + body)
    │
    └──► [--tts] Mistral TTS → .mp3
```

## Modules

| File                      | Role                                         |
|---------------------------|----------------------------------------------|
| `pipeline/cli.py`         | Entry point, argument parsing, orchestration |
| `pipeline/downloader.py`  | yt-dlp wrapper, returns `VideoMeta`          |
| `pipeline/transcribe.py`  | Voxtral STT call                             |
| `pipeline/postprocess.py` | LLM cleanup and optional EN translation      |
| `pipeline/tagger.py`      | LLM tag generation                           |
| `pipeline/presenter.py`   | Speaker name extraction                      |
| `pipeline/frontmatter.py` | Obsidian YAML frontmatter builder            |
| `pipeline/tts.py`         | Mistral TTS synthesis                        |
| `pipeline/prompts.py`     | All LLM system instructions                  |
| `pipeline/env_loader.py`  | `.env` / `.env.prod` loader                  |
