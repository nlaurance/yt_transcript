"""Convert text to MP3 via Mistral Voxtral TTS.

API: https://docs.mistral.ai/studio-api/audio/text_to_speech/speech
Voices: https://docs.mistral.ai/studio-api/audio/text_to_speech/voices

Pass a preset ``slug`` from ``audio.voices.list()`` (e.g. ``fr_marie_neutral``)
or a custom voice UUID from ``audio.voices.create()``.
"""

import base64
import re
import subprocess
import tempfile
from pathlib import Path

from mistralai.client import Mistral

# https://docs.mistral.ai/studio-api/audio/text_to_speech/speech
TTS_MODEL = "voxtral-mini-tts-2603"

DEFAULT_VOICE_SLUG = "fr_marie_neutral"
DEFAULT_VOICE_BY_LANG = {
    "fr": "fr_marie_neutral",
    "en": "en_paul_neutral",
}
TTS_LANGS = frozenset(DEFAULT_VOICE_BY_LANG)

# Mistral recommends <300 words per request for best quality.
_MAX_WORDS_PER_CHUNK = 250

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def default_voice_slug(language: str) -> str:
    if language not in DEFAULT_VOICE_BY_LANG:
        raise ValueError(f"TTS requires language fr or en, got {language!r}")
    return DEFAULT_VOICE_BY_LANG[language]


def assert_voice_matches_lang(voice: str, language: str) -> None:
    """Ensure preset voice slug matches script language (avoids cross-lingual accent)."""
    voice = voice.strip()
    if _UUID_RE.match(voice):
        return
    if language == "fr" and not voice.startswith("fr_"):
        raise ValueError(
            f"Voice {voice!r} does not match --lang fr. "
            f"Use a French slug (e.g. {DEFAULT_VOICE_BY_LANG['fr']})."
        )
    if language == "en" and not (voice.startswith("en_") or voice.startswith("gb_")):
        raise ValueError(
            f"Voice {voice!r} does not match --lang en. "
            f"Use an English slug (e.g. {DEFAULT_VOICE_BY_LANG['en']})."
        )


def _voice_uuid(client: Mistral, voice: str) -> str:
    voice = voice.strip()
    if _UUID_RE.match(voice):
        return voice
    offset = 0
    while True:
        resp = client.audio.voices.list(limit=50, offset=offset, type_="all")
        for v in resp.items:
            if v.slug == voice:
                return v.id
        if offset + len(resp.items) >= resp.total:
            break
        offset += len(resp.items)
    raise ValueError(
        f"Unknown voice {voice!r}. Use a slug from audio.voices.list() "
        "(e.g. fr_marie_neutral) or a custom voice UUID."
    )


def synthesize(
    text: str,
    output_path: Path,
    client: Mistral,
    voice: str = DEFAULT_VOICE_SLUG,
) -> None:
    """Render *text* to speech and write the result to *output_path* (MP3).

    Long scripts are split into word-bounded chunks (see Mistral best practices),
    synthesized separately, then concatenated with ffmpeg when needed.

    Args:
        text: Narrative script (Markdown syntax is stripped).
        output_path: Destination MP3 file path.
        client: Authenticated Mistral client.
        voice: Voice slug or custom UUID.
    """
    clean_text = prepare_for_tts(text)
    voice_id = _voice_uuid(client, voice)
    chunks = _chunk_text(clean_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if len(chunks) == 1:
        _synthesize_chunk(chunks[0], output_path, client, voice_id)
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        part_paths: list[Path] = []
        for i, chunk in enumerate(chunks):
            part = tmp_dir / f"part_{i:03d}.mp3"
            _synthesize_chunk(chunk, part, client, voice_id)
            part_paths.append(part)
        _concat_mp3(part_paths, output_path)


def _synthesize_chunk(
    text: str,
    output_path: Path,
    client: Mistral,
    voice_id: str,
) -> None:
    response = client.audio.speech.complete(
        model=TTS_MODEL,
        input=text,
        voice_id=voice_id,
        response_format="mp3",
    )
    output_path.write_bytes(base64.b64decode(response.audio_data))


def _chunk_text(text: str, max_words: int = _MAX_WORDS_PER_CHUNK) -> list[str]:
    """Split on paragraph boundaries when possible, else by word count."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return [text] if text.strip() else [""]

    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if para_words > max_words:
            if current:
                chunks.append("\n\n".join(current))
                current, current_words = [], 0
            words = para.split()
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i : i + max_words]))
            continue

        if current_words + para_words > max_words and current:
            chunks.append("\n\n".join(current))
            current, current_words = [para], para_words
        else:
            current.append(para)
            current_words += para_words

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _concat_mp3(parts: list[Path], output_path: Path) -> None:
    if len(parts) == 1:
        output_path.write_bytes(parts[0].read_bytes())
        return

    list_file = output_path.with_suffix(".concat.txt")
    list_file.write_text(
        "\n".join(f"file '{p.resolve()}'" for p in parts),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    list_file.unlink(missing_ok=True)


def prepare_for_tts(text: str) -> str:
    """Normalize narrative text for Mistral TTS (https://docs.mistral.ai/.../speech)."""
    text = _strip_markdown(text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = _EMOJI_RE.sub("", text)
    text = re.sub(r"[^\S\n]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"
    "\U0001F600-\U0001F64F"
    "\U00002600-\U000027BF"
    "\U0000FE00-\U0000FE0F"
    "]+",
    flags=re.UNICODE,
)


def _strip_markdown(text: str) -> str:
    """Remove Markdown syntax that would be read aloud literally by TTS."""
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,3}(.+?)_{1,3}", r"\1", text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
