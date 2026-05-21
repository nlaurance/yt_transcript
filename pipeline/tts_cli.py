"""Generate MP3 from an existing narrative .txt (retry TTS without re-running the pipeline).

Usage
-----
    uv run --group pipeline yt-transcript-tts path/to/script.txt --lang fr|en [options]

See https://docs.mistral.ai/studio-api/audio/text_to_speech/speech
"""

import argparse
import os
import sys
from pathlib import Path

from mistralai.client import Mistral
from mistralai.client.errors import SDKError

from pipeline.env_loader import env_path, load_env, mistral_timeout_ms
from pipeline.output_paths import resolve_output
from pipeline.tts import (
    assert_voice_matches_lang,
    default_voice_slug,
    synthesize,
)


def _resolve_audio_output(narrative: Path, spec: str | None, default_dir: Path) -> Path:
    if spec:
        audio_spec = Path(spec).expanduser()
        is_mp3_file = (
            audio_spec.suffix == ".mp3"
            and not (audio_spec.exists() and audio_spec.is_dir())
        )
        if is_mp3_file:
            return audio_spec
        stem = narrative.stem
        return resolve_output(spec, default_dir, stem, ".mp3")
    return narrative.with_suffix(".mp3")


def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(
        prog="yt-transcript-tts",
        description="Generate MP3 from a narrative .txt via Mistral TTS.",
    )
    parser.add_argument(
        "narrative",
        type=Path,
        help="Plain-text narrative script (.txt)",
    )
    parser.add_argument(
        "--lang",
        required=True,
        choices=["fr", "en"],
        help="Script language: selects default TTS voice (fr_marie_* / en_paul_* or gb_*)",
    )
    parser.add_argument(
        "--audio-voice",
        default=None,
        dest="audio_voice",
        metavar="SLUG_OR_UUID",
        help=(
            "Mistral voice slug (must match --lang) or custom UUID; "
            "env: YT_TRANSCRIPT_AUDIO_VOICE; default: fr_marie_neutral or en_paul_neutral"
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=env_path("YT_TRANSCRIPT_OUTPUT_DIR") or "output",
        dest="output_dir",
        help="Default output directory when --audio-output is a directory",
    )
    parser.add_argument(
        "--audio-output",
        default=env_path("YT_TRANSCRIPT_AUDIO_OUTPUT"),
        dest="audio_output",
        metavar="PATH",
        help="MP3 file or directory (default: <narrative>.mp3 beside the script)",
    )
    args = parser.parse_args()

    narrative = args.narrative.expanduser()
    if not narrative.is_file():
        print(f"ERROR: narrative file not found: {narrative}", file=sys.stderr)
        sys.exit(1)
    if narrative.suffix.lower() != ".txt":
        print(f"ERROR: expected a .txt file: {narrative}", file=sys.stderr)
        sys.exit(1)

    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        print("ERROR: MISTRAL_API_KEY is not set.", file=sys.stderr)
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

    client = Mistral(api_key=api_key, timeout_ms=mistral_timeout_ms())
    text = narrative.read_text(encoding="utf-8")
    if not text.strip():
        print(f"ERROR: narrative file is empty: {narrative}", file=sys.stderr)
        sys.exit(1)

    default_dir = Path(args.output_dir)
    tts_path = _resolve_audio_output(narrative, args.audio_output, default_dir)

    try:
        print(f"Voice: {voice}")
        print(f"Generating audio via Mistral TTS ({len(text.split())} words)...")
        synthesize(text, tts_path, client, voice=voice)
        print(f"Generated audio → {tts_path}")
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except SDKError as e:
        if "invalid_voice" in str(e) or "not found" in str(e).lower():
            print(
                f"\nERROR: {e}\n"
                "  List voices: https://docs.mistral.ai/studio-api/audio/text_to_speech/voices\n"
                "  Use a slug like fr_marie_neutral or a custom voice UUID.",
                file=sys.stderr,
            )
        else:
            print(f"\nERROR: Mistral API error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
