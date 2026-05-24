# yt-transcript

YouTube audio → synthetic technical note, optional podcast script, optional re-narrated MP3.

Downloads a video’s audio, transcribes it with Mistral Voxtral, then uses Mistral Small to
produce a dense **synthetic note** (Obsidian-ready Markdown). Optionally adds a **narrative**
script suited for text-to-speech, and optionally synthesizes an MP3 from that script.

Supports French and English presentations (`--lang fr|en|auto`).

## What you get

### Always

| Artifact       | Default path            | Description                                                                                |
|----------------|-------------------------|--------------------------------------------------------------------------------------------|
| Synthetic note | `output/<slug>.md`      | Cleaned talk: headings, tables, code, `## Documentation Technique` block, YAML frontmatter |
| Raw transcript | `output/<slug>_raw.txt` | Unedited Voxtral output (kept for reference)                                               |

### With `--narrative` or `--audio`

| Artifact       | Default path                                  | Description                          |
|----------------|-----------------------------------------------|--------------------------------------|
| Narrative text | same dir as raw (`<slug>_narrative.txt`)      | Plain script for TTS retries / edits |
| Narrative note | `YT_TRANSCRIPT_NARRATIVE_OUTPUT` or `output/` | Same script + Obsidian frontmatter   |

`--audio` implies narrative generation (you do not need both flags for a podcast workflow).

### With `--audio`

| Artifact      | Default path                  | Description                              |
|---------------|-------------------------------|------------------------------------------|
| Generated MP3 | `output/<slug>_narrative.mp3` | Mistral TTS reading the narrative `.txt` |

### With `--audio-output`

| Artifact   | Default path          | Description                          |
|------------|-----------------------|--------------------------------------|
| Source MP3 | `…/<slug>_source.mp3` | Copy of the downloaded YouTube audio |

Without `--audio-output`, the download cache under `output/_cache/` is deleted after a
successful run.

### With `--translate-summary`

Appends an English translation of the technical documentation block to the synthetic note
(French talks only).

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- [ffmpeg](https://ffmpeg.org/) — `brew install ffmpeg`
- A [Mistral API key](https://console.mistral.ai/api-keys) with Voxtral enabled

## Setup

```bash
cp .env.example .env
# Set MISTRAL_API_KEY=...
# Optional: set YT_TRANSCRIPT_OUTPUT_DIR, YT_TRANSCRIPT_NOTE_OUTPUT, etc.

uv sync --group pipeline
```

## Usage

Default language is **French**. Use `--lang en` for English talks, or `--lang auto` to let
Voxtral detect the language.

```bash
# Synthetic note + raw transcript only
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX"

# English talk
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" --lang en

# Narrative script (.txt + .md), no audio
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" --narrative

# Podcast: narrative + MP3 (--audio implies --narrative)
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" --audio

# Full example: split outputs, English summary, custom voice
uv run --group pipeline yt-transcript "https://www.youtube.com/watch?v=XXX" \
  --lang en \
  --note-output ~/vault/notes \
  --raw-output ~/vault/raw \
  --narrative-output ~/vault/narrative \
  --audio-output ~/vault/audio \
  --audio \
  --audio-voice en_paul_neutral \
  --translate-summary
```

### Retry TTS from an existing narrative

If the pipeline succeeded but TTS failed (or you want a different voice), regenerate
the MP3 from a saved `*_narrative.txt` without re-downloading or re-transcribing:

```bash
# --lang is required (fr → fr_marie_*, en → en_paul_* / gb_*)
uv run --group pipeline yt-transcript-tts ~/vault/my-talk_narrative.txt --lang en

uv run --group pipeline yt-transcript-tts script.txt --lang fr \
  --audio-voice fr_marie_happy \
  --audio-output ~/vault/my-talk.mp3
```

Voices use slugs from [audio.voices.list()](https://docs.mistral.ai/studio-api/audio/text_to_speech/voices)
as `voice_id` in
[speech generation](https://docs.mistral.ai/studio-api/audio/text_to_speech/speech).

Available preset voice slugs (snapshot from the API on 2026-05-23):

| Family      | Slugs                                                                                                                                                                         |
|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `fr_marie`  | `fr_marie_angry`, `fr_marie_curious`, `fr_marie_excited`, `fr_marie_happy`, `fr_marie_neutral`, `fr_marie_sad`                                                                |
| `en_paul`   | `en_paul_angry`, `en_paul_cheerful`, `en_paul_confident`, `en_paul_excited`, `en_paul_frustrated`, `en_paul_happy`, `en_paul_neutral`, `en_paul_sad`                          |
| `gb_jane`   | `gb_jane_confident`, `gb_jane_confused`, `gb_jane_curious`, `gb_jane_frustrated`, `gb_jane_jealousy`, `gb_jane_neutral`, `gb_jane_sad`, `gb_jane_sarcasm`, `gb_jane_shameful` |
| `gb_oliver` | `gb_oliver_angry`, `gb_oliver_cheerful`, `gb_oliver_confident`, `gb_oliver_curious`, `gb_oliver_excited`, `gb_oliver_neutral`, `gb_oliver_sad`                                |

Current total from `audio.voices.list(type_="all")`: **30 voices**.
Use a custom voice UUID as `--audio-voice` if you created one with `audio.voices.create()`.

### Output paths

`--output-dir` (or `YT_TRANSCRIPT_OUTPUT_DIR` in `.env`) is the fallback when a
per-artifact flag is omitted. Env vars are loaded from `.env` / `.env.prod`; CLI flags
override env when both are set.

Each path flag accepts a **directory** (files named from the video slug) or an explicit **file**:

| Flag                 | Formats | Always / conditional                                         |
|----------------------|---------|--------------------------------------------------------------|
| `--note-output`      | `.md`   | Always (synthetic note)                                      |
| `--raw-output`       | `.txt`  | Always (raw transcript)                                      |
| `--narrative-output` | `.md`   | With `--narrative` or `--audio` (`.txt` uses `--raw-output`) |
| `--audio-output`     | `.mp3`  | Source copy always; generated MP3 with `--audio`             |

Examples:

```bash
# Exact note file; other artifacts use default output/
uv run --group pipeline yt-transcript "URL" \
  --note-output ~/vault/my-talk.md

# Exact raw transcript file
uv run --group pipeline yt-transcript "URL" \
  --raw-output ~/vault/my-talk_raw.txt

# Narrative .md in vault; plain .txt in the raw directory
uv run --group pipeline yt-transcript "URL" --narrative \
  --raw-output ~/vault/raw \
  --narrative-output ~/vault/Narratives

# Generated MP3 to a specific file; source audio in a directory
uv run --group pipeline yt-transcript "URL" --audio \
  --audio-output ~/vault/my-talk.mp3
```

When `--audio-output` points to a single `.mp3` file, that path is used for the generated
audio; the source download is saved as `<stem>_source.mp3` in the same directory.

## Options

| Flag                  | Default     | Description                                                                                                    |
|-----------------------|-------------|----------------------------------------------------------------------------------------------------------------|
| `--lang`              | `fr`        | Source language: `fr`, `en`, or `auto`                                                                         |
| `--narrative`         | off         | Add `*_narrative.txt` and `*_narrative.md` (synthetic note still always written)                               |
| `--audio`             | off         | Generate MP3 from narrative; also generates and saves narrative text                                           |
| `--translate-summary` | off         | Append English translation of the technical docs block                                                         |
| `--audio-voice`       | by `--lang` | Mistral voice slug (`fr_marie_neutral`, `en_paul_neutral`, …) or custom UUID; env: `YT_TRANSCRIPT_AUDIO_VOICE` |
| `--output-dir`        | `./output`  | Default directory (`YT_TRANSCRIPT_OUTPUT_DIR`)                                                                 |
| `--note-output`       | (dir)       | Synthetic note (`YT_TRANSCRIPT_NOTE_OUTPUT`)                                                                   |
| `--raw-output`        | (dir)       | Raw transcript (`YT_TRANSCRIPT_RAW_OUTPUT`)                                                                    |
| `--narrative-output`  | (dir)       | Narrative Obsidian `.md` (`YT_TRANSCRIPT_NARRATIVE_OUTPUT`)                                                    |
| `--audio-output`      | —           | Audio files (`YT_TRANSCRIPT_AUDIO_OUTPUT`)                                                                     |

## Pipeline

```
YouTube URL
    │
    ▼  yt-dlp + ffmpeg
MP3 (cached under output/_cache/)
    │
    ▼  Mistral Voxtral
Raw transcript ──────────────────────────► <slug>_raw.txt  (always)
    │
    ├──► presenter extraction (metadata → LLM fallback)
    │
    ▼  Mistral Small: clean()
    │      filler removal, restructuring, documentation block
    │
    ├──► [--translate-summary] EN docs block appended to note
    ├──► [--narrative | --audio] narrative() on cleaned text
    │         (prose, no code; second LLM pass)
    │
    ▼  wrap_lines / format_tables  (synthetic note only)
    │
    ▼  YAML frontmatter + tags
    │
    ├──► <slug>.md                    synthetic note (always)
    ├──► <slug>_narrative.txt (raw dir) + .md (narrative-output)   optional
    ├──► [--audio-output] <slug>_source.mp3
    └──► [--audio] <slug>_narrative.mp3   TTS from narrative .txt
```

**Order:** Voxtral → **`clean()`** (synthetic note content) → optional **`narrative()`**
(rewrite for listening, same substance, no code) → formatting on the note only.

## Modules

| File                       | Role                                       |
|----------------------------|--------------------------------------------|
| `pipeline/cli.py`          | Entry point, orchestration                 |
| `pipeline/output_paths.py` | Output path resolution (file vs directory) |
| `pipeline/downloader.py`   | yt-dlp wrapper, `VideoMeta`                |
| `pipeline/transcribe.py`   | Voxtral STT                                |
| `pipeline/postprocess.py`  | `clean()`, `narrative()`, translation      |
| `pipeline/tagger.py`       | Content tags                               |
| `pipeline/presenter.py`    | Speaker name                               |
| `pipeline/frontmatter.py`  | Obsidian YAML frontmatter                  |
| `pipeline/tts.py`          | Mistral TTS                                |
| `pipeline/prompts.py`      | LLM system prompts                         |
| `pipeline/env_loader.py`   | `.env` loader                              |
