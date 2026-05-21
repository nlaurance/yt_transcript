"""yt-transcript — YouTube → Obsidian Markdown pipeline.

Downloads the audio of a YouTube video, transcribes it via Mistral Voxtral,
cleans and structures the text, generates Obsidian-compatible frontmatter with
content tags, and optionally produces a re-narrated MP3.

Usage
-----
    uv run --group pipeline yt-transcript <URL> [options]

Options
-------
    --lang fr|en|auto   Source language (default: fr).
    --tts               Generate a re-narrated MP3 from the processed text.
    --translate-summary Append an English translation of the technical docs block.
    --tts-voice         Mistral TTS voice: sasha (default) or benjamin.
    --output-dir PATH   Output directory (default: ./output).

Examples
--------
    yt-transcript "https://www.youtube.com/watch?v=XXX"
    yt-transcript "https://www.youtube.com/watch?v=XXX" --lang en --tts
    yt-transcript "https://www.youtube.com/watch?v=XXX" --translate-summary
"""

import argparse
import os
import sys
from pathlib import Path

from slugify import slugify

from pipeline import postprocess, tagger, transcribe
from pipeline.downloader import download_audio
from pipeline.env_loader import load_env
from pipeline import frontmatter as fm
from pipeline.presenter import extract_presenter
from pipeline.tts import synthesize


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="yt-transcript",
        description="YouTube → clean Obsidian Markdown transcript via Mistral.",
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--lang",
        default="fr",
        choices=["fr", "en", "auto"],
        help="Source language (default: fr)",
    )
    parser.add_argument(
        "--tts",
        action="store_true",
        help="Generate a re-narrated MP3 from the processed transcript",
    )
    parser.add_argument(
        "--translate-summary",
        action="store_true",
        dest="translate_summary",
        help="Append an English translation of the technical documentation block",
    )
    parser.add_argument(
        "--tts-voice",
        default="sasha",
        choices=["sasha", "benjamin"],
        dest="tts_voice",
        help="Mistral TTS voice (default: sasha)",
    )
    parser.add_argument(
        "--output-dir",
        default="output",
        dest="output_dir",
        help="Directory for output files (default: ./output)",
    )
    args = parser.parse_args()

    # --- Environment ---
    load_env()
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    from mistralai.client import Mistral
    client = Mistral(api_key=api_key)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lang = None if args.lang == "auto" else args.lang
    mp3_path = None

    try:
        # 1. Download
        print(f"Downloading audio from: {args.url}")
        meta = download_audio(args.url, output_dir / "_tmp")
        mp3_path = meta.mp3_path
        print(f"  → {mp3_path.name}  ({meta.duration_seconds // 60} min)")

        # 2. Transcribe
        print("Transcribing via Voxtral...")
        raw = transcribe.transcribe(mp3_path, client, language=lang)
        print(f"  → {len(raw.split())} words in raw transcript")

        # 3. Extract presenter name (metadata first, LLM fallback)
        print("Extracting presenter name...")
        presenter = extract_presenter(meta, raw, client)
        print(f"  → {presenter or '(not found)'}")

        # 4. Clean and structure
        print("Cleaning transcript and generating documentation block...")
        processed = postprocess.clean(raw, client, language=args.lang)

        # 5. Translate summary if requested
        if args.translate_summary:
            print("Translating technical documentation block to English...")
            en_summary = postprocess.translate_summary(processed, client)
            processed = processed + "\n\n---\n\n" + en_summary

        # 6. Generate tags
        print("Generating content tags...")
        tags = tagger.generate_tags(processed, client)
        print(f"  → {', '.join(tags)}")

        # 7. Assemble Obsidian Markdown
        frontmatter_block = fm.build(meta, presenter, tags, args.lang)
        full_document = frontmatter_block + processed

        # 8. Write Markdown output
        slug = slugify(meta.title, max_length=80, separator="_")
        md_path = output_dir / f"{slug}.md"
        md_path.write_text(full_document, encoding="utf-8")
        print(f"\nMarkdown saved → {md_path}")

        # 9. Optional TTS
        if args.tts:
            print("Generating audio via Mistral TTS...")
            tts_path = output_dir / f"{slug}.mp3"
            synthesize(processed, tts_path, client, voice=args.tts_voice)
            print(f"Audio saved    → {tts_path}")

    finally:
        if mp3_path and mp3_path.exists():
            mp3_path.unlink()
        tmp_dir = output_dir / "_tmp"
        if tmp_dir.exists() and not any(tmp_dir.iterdir()):
            tmp_dir.rmdir()


if __name__ == "__main__":
    main()
