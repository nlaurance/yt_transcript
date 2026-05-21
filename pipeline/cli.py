"""yt-transcript — YouTube → Obsidian Markdown pipeline.

Downloads the audio of a YouTube video, transcribes it via Mistral Voxtral,
always produces a synthetic note (structured Markdown), optionally a narrative
podcast script on top, and optionally a re-narrated MP3.

Usage
-----
    uv run --group pipeline yt-transcript <URL> [options]

Options
-------
    --lang fr|en|auto   Source language (default: fr).
    --narrative         Optional podcast script (.txt + .md) on top of the synthetic note.
    --audio             MP3 from narrative script (implies --narrative).
    --narrative-output PATH  Plain .txt and Obsidian .md for the podcast script.
    --translate-summary Append an English translation of the technical docs block.
    --audio-voice       Mistral voice slug (default by --lang) or custom UUID.
    --output-dir PATH   Default directory (or YT_TRANSCRIPT_OUTPUT_DIR in .env).
    --note-output PATH  Synthetic note (or YT_TRANSCRIPT_NOTE_OUTPUT).
    --raw-output PATH   Raw transcript (or YT_TRANSCRIPT_RAW_OUTPUT).
    --narrative-output PATH  Narrative script (or YT_TRANSCRIPT_NARRATIVE_OUTPUT).
    --audio-output PATH  Audio files (or YT_TRANSCRIPT_AUDIO_OUTPUT).

Examples
--------
    yt-transcript "https://www.youtube.com/watch?v=XXX"
    yt-transcript "https://www.youtube.com/watch?v=XXX" --lang en --narrative --audio
    yt-transcript "https://www.youtube.com/watch?v=XXX" \\
        --note-output ~/notes/talks --raw-output ~/notes/raw --audio-output ~/notes/audio
"""

import argparse
import os
import shutil
import sys
from pathlib import Path

from mistralai.client.errors import SDKError

from slugify import slugify

from pipeline import postprocess, tagger, transcribe
from pipeline.downloader import download_audio
from pipeline.env_loader import env_path, load_env, mistral_timeout_ms
from pipeline import frontmatter as fm
from pipeline.format_tables import format_tables
from pipeline.output_paths import resolve_output
from pipeline.presenter import extract_presenter
from pipeline.tts import assert_voice_matches_lang, default_voice_slug, synthesize
from pipeline.wrap_lines import wrap_lines


def _write_narrative(
    narrative_body: str,
    frontmatter_block: str,
    slug: str,
    default_dir: Path,
    narrative_output: str | None,
) -> None:
    """Write plain-text script (.txt) and Obsidian companion (.md)."""
    spec = Path(narrative_output).expanduser() if narrative_output else None
    if spec and spec.suffix == ".md" and not (spec.exists() and spec.is_dir()):
        md_path = spec
        md_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path = md_path.with_suffix(".txt")
    elif spec and spec.suffix == ".txt" and not (spec.exists() and spec.is_dir()):
        txt_path = spec
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        md_path = txt_path.with_suffix(".md")
    else:
        txt_path = resolve_output(narrative_output, default_dir, f"{slug}_narrative", ".txt")
        md_path = resolve_output(narrative_output, default_dir, f"{slug}_narrative", ".md")

    txt_path.write_text(narrative_body, encoding="utf-8")
    md_path.write_text(frontmatter_block + narrative_body, encoding="utf-8")
    print(f"Narrative text → {txt_path}")
    print(f"Narrative note → {md_path}")


def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(
        prog="yt-transcript",
        description=(
            "YouTube → synthetic note (always), optional narrative script, optional MP3."
        ),
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--lang",
        default="fr",
        choices=["fr", "en", "auto"],
        help="Source language (default: fr)",
    )
    parser.add_argument(
        "--narrative",
        action="store_true",
        help="Also write podcast script as *_narrative.txt (plain) and .md; note is always produced",
    )
    parser.add_argument(
        "--audio",
        action="store_true",
        help="Generate MP3 from narrative script (also generates and saves narrative text)",
    )
    parser.add_argument(
        "--translate-summary",
        action="store_true",
        dest="translate_summary",
        help="Append an English translation of the technical documentation block",
    )
    parser.add_argument(
        "--audio-voice",
        default=None,
        dest="audio_voice",
        metavar="SLUG_OR_UUID",
        help=(
            "Mistral voice slug (e.g. fr_marie_neutral) or custom UUID; "
            "env: YT_TRANSCRIPT_AUDIO_VOICE; default by --lang"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=env_path("YT_TRANSCRIPT_OUTPUT_DIR") or "output",
        dest="output_dir",
        help="Default output directory (env: YT_TRANSCRIPT_OUTPUT_DIR, default: ./output)",
    )
    parser.add_argument(
        "--note-output",
        default=env_path("YT_TRANSCRIPT_NOTE_OUTPUT"),
        dest="note_output",
        metavar="PATH",
        help="Synthetic note .md path (env: YT_TRANSCRIPT_NOTE_OUTPUT)",
    )
    parser.add_argument(
        "--raw-output",
        default=env_path("YT_TRANSCRIPT_RAW_OUTPUT"),
        dest="raw_output",
        metavar="PATH",
        help="Raw transcript .txt path (env: YT_TRANSCRIPT_RAW_OUTPUT)",
    )
    parser.add_argument(
        "--narrative-output",
        default=env_path("YT_TRANSCRIPT_NARRATIVE_OUTPUT"),
        dest="narrative_output",
        metavar="PATH",
        help="Narrative .txt/.md path (env: YT_TRANSCRIPT_NARRATIVE_OUTPUT)",
    )
    parser.add_argument(
        "--audio-output",
        default=env_path("YT_TRANSCRIPT_AUDIO_OUTPUT"),
        dest="audio_output",
        metavar="PATH",
        help="Source/generated MP3 path (env: YT_TRANSCRIPT_AUDIO_OUTPUT)",
    )
    args = parser.parse_args()
    args.url = args.url.replace("\\", "")

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY is not set.", file=sys.stderr)
        sys.exit(1)

    from mistralai.client import Mistral
    client = Mistral(api_key=api_key, timeout_ms=mistral_timeout_ms())

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lang = None if args.lang == "auto" else args.lang
    mp3_path = None
    success = False
    slug: str | None = None

    try:
        # 1. Download (reuses cache if available)
        print(f"Downloading audio from: {args.url}")
        meta = download_audio(args.url, output_dir)
        mp3_path = meta.mp3_path
        print(f"  → {mp3_path.name}  ({meta.duration_seconds // 60} min)")

        slug = slugify(meta.title, max_length=80, separator="_")

        # 2. Transcribe
        print("Transcribing via Voxtral...")
        raw = transcribe.transcribe(mp3_path, client, language=lang)
        print(f"  → {len(raw.split())} words in raw transcript")

        raw_path = resolve_output(args.raw_output, output_dir, f"{slug}_raw", ".txt")
        raw_path.write_text(raw, encoding="utf-8")
        print(f"Raw transcript → {raw_path}")

        # 3. Extract presenter name (metadata first, LLM fallback)
        print("Extracting presenter name...")
        presenter = extract_presenter(meta, raw, client)
        print(f"  → {presenter or '(not found)'}")

        # 4. Synthetic note (always): clean() then optional narrative() on top
        print("Building synthetic note (cleanup + documentation block)...")
        processed = postprocess.clean(raw, client, language=args.lang)

        # 5. Translate summary if requested
        if args.translate_summary:
            print("Translating technical documentation block to English...")
            en_summary = postprocess.translate_summary(processed, client)
            processed = processed + "\n\n---\n\n" + en_summary

        want_narrative = args.narrative or args.audio
        narrative_body: str | None = None
        if want_narrative:
            print("Generating linear podcast script...")
            narrative_body = postprocess.narrative(processed, client, language=args.lang)
            narrative_body = wrap_lines(narrative_body)
            print(f"  → {len(narrative_body.split())} words in narrative script")

        # 6. Generate tags
        print("Generating content tags...")
        tags = tagger.generate_tags(processed, client)
        print(f"  → {', '.join(tags)}")

        # 7. Post-production formatting (deterministic, no LLM)
        processed = wrap_lines(processed)
        processed = format_tables(processed)

        # 8. Assemble Obsidian Markdown
        frontmatter_block = fm.build(meta, presenter, tags, args.lang)
        full_document = frontmatter_block + processed

        md_path = resolve_output(args.note_output, output_dir, slug, ".md")
        md_path.write_text(full_document, encoding="utf-8")
        print(f"\nMarkdown saved → {md_path}")

        if narrative_body is not None:
            narrative_dir = md_path.parent
            _write_narrative(
                narrative_body,
                frontmatter_block,
                slug,
                narrative_dir,
                args.narrative_output,
            )

        if args.audio_output:
            audio_spec = Path(args.audio_output).expanduser()
            is_mp3_file = (
                audio_spec.suffix == ".mp3"
                and not (audio_spec.exists() and audio_spec.is_dir())
            )
            if is_mp3_file:
                source_dest = audio_spec.with_name(f"{audio_spec.stem}_source{audio_spec.suffix}")
            else:
                source_dest = resolve_output(args.audio_output, output_dir, f"{slug}_source", ".mp3")
            source_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mp3_path, source_dest)
            print(f"Source audio   → {source_dest}")

        if args.audio:
            if narrative_body is None:
                print("ERROR: --audio requires a narrative script.", file=sys.stderr)
                sys.exit(1)
            if args.lang == "auto":
                print(
                    "ERROR: --audio requires --lang fr or --lang en (not auto).",
                    file=sys.stderr,
                )
                sys.exit(1)
            voice = (
                args.audio_voice
                or env_path("YT_TRANSCRIPT_AUDIO_VOICE")
                or default_voice_slug(args.lang)
            )
            try:
                assert_voice_matches_lang(voice, args.lang)
            except ValueError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                sys.exit(1)
            print(f"Generating audio via Mistral TTS (voice: {voice})...")
            gen_stem = f"{slug}_narrative"
            audio_spec = Path(args.audio_output).expanduser() if args.audio_output else None
            is_mp3_file = (
                audio_spec is not None
                and audio_spec.suffix == ".mp3"
                and not (audio_spec.exists() and audio_spec.is_dir())
            )
            tts_path = audio_spec if is_mp3_file else resolve_output(
                args.audio_output, output_dir, gen_stem, ".mp3",
            )
            synthesize(narrative_body, tts_path, client, voice=voice)
            print(f"Generated audio → {tts_path}")

        success = True

    except ValueError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)

    except SDKError as e:
        if "invalid_voice" in str(e) or "not found" in str(e).lower():
            print(
                f"\nERROR: {e}\n"
                "  List voices: https://docs.mistral.ai/studio-api/audio/text_to_speech/voices\n"
                "  Retry TTS only: uv run --group pipeline yt-transcript-tts <narrative.txt>",
                file=sys.stderr,
            )
        elif "401" in str(e) or "Unauthorized" in str(e):
            print(
                "\nERROR: Mistral API returned 401 Unauthorized.\n"
                "  - Check that MISTRAL_API_KEY is correct in your .env file.\n"
                "  - Voxtral (audio transcription) requires explicit activation on your\n"
                "    Mistral account: https://console.mistral.ai/api-keys\n"
                "  - The cached audio file has been kept — rerun once the key is fixed.",
                file=sys.stderr,
            )
        else:
            print(f"\nERROR: Mistral API error: {e}", file=sys.stderr)
        sys.exit(1)

    finally:
        # Remove download cache after success; use --audio-output to keep a copy
        if success and mp3_path and mp3_path.exists() and not args.audio_output:
            mp3_path.unlink()
            cache_dir = output_dir / "_cache"
            if cache_dir.exists() and not any(cache_dir.iterdir()):
                cache_dir.rmdir()


if __name__ == "__main__":
    main()
