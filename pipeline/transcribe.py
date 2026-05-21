"""Transcribe an MP3 file to text using Mistral Voxtral (STT).

Voxtral handles both French and English with high accuracy.
Pass language="fr", language="en", or language=None for auto-detection.
"""

from pathlib import Path

from mistralai.client import Mistral


def transcribe(mp3_path: Path, client: Mistral, language: str | None = "fr") -> str:
    """Upload *mp3_path* to Voxtral and return the raw transcript text.

    Args:
        mp3_path: Path to the local MP3 file.
        client: Authenticated Mistral client.
        language: BCP-47 language code ("fr", "en") or None for auto-detection.

    Returns:
        Raw transcript string (no punctuation cleanup, no paragraph breaks).
    """
    with open(mp3_path, "rb") as f:
        audio_bytes = f.read()

    kwargs: dict = {
        "model": "voxtral-mini-latest",
        "file": {"file_name": mp3_path.name, "content": audio_bytes},
    }
    if language:
        kwargs["language"] = language

    response = client.audio.transcriptions.complete(**kwargs)
    return response.text
