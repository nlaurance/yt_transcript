"""Convert the processed Markdown document to a natural-sounding MP3 via Mistral TTS.

Markdown syntax characters are stripped before synthesis so the TTS engine
reads clean prose rather than literal '#' or '*' characters.
"""

import base64
import re
from pathlib import Path

from mistralai.client import Mistral


def synthesize(text: str, output_path: Path, client: Mistral, voice: str = "sasha") -> None:
    """Render *text* to speech and write the result to *output_path* (MP3).

    Args:
        text: Processed Markdown document (frontmatter is excluded by caller).
        output_path: Destination MP3 file path.
        client: Authenticated Mistral client.
        voice: Mistral TTS voice identifier ("sasha" or "benjamin").
    """
    clean_text = _strip_markdown(text)

    response = client.audio.speech.complete(
        input=clean_text,
        voice_id=voice,
        response_format="mp3",
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(response.audio_data))


def _strip_markdown(text: str) -> str:
    """Remove Markdown syntax that would be read aloud literally by TTS."""
    # Remove YAML frontmatter block
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    # Remove headings markers
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    # Remove inline code and code blocks
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Remove table pipes (leave cell content)
    text = re.sub(r"\|", " ", text)
    # Remove bullet/list markers
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    # Collapse excess blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
