"""Extract the presenter's name from video metadata or transcript opening.

Stage 1 — yt-dlp metadata:
  Tries common patterns in title, uploader, and description before making
  any API call.

Stage 2 — LLM fallback:
  If metadata extraction is not confident, passes the first ~300 words of
  the raw transcript to Mistral to extract a speaker self-introduction.
"""

import re

from mistralai.client import Mistral

from pipeline.downloader import VideoMeta
from pipeline.prompts import PRESENTER_EXTRACTION_PROMPT

# Patterns that reliably signal a person's name follows
_METADATA_PATTERNS = [
    r"(?:by|par|avec|—|-)\s+([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+(?:\s+[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+)+)",
    r"([A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+(?:\s+[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+)+)\s*[|–—-]",
]


def extract_presenter(meta: VideoMeta, raw_transcript: str, client: Mistral) -> str | None:
    """Return the presenter's name, or None if it cannot be determined.

    Tries metadata first (free), falls back to a lightweight LLM call.
    """
    name = _from_metadata(meta)
    if name:
        return name
    return _from_transcript(raw_transcript, client)


def _from_metadata(meta: VideoMeta) -> str | None:
    candidates = [meta.title, meta.uploader, meta.description[:500]]
    for text in candidates:
        for pattern in _METADATA_PATTERNS:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

    # If the uploader looks like a personal name (two capitalised words, no
    # special chars) use it directly
    uploader = meta.uploader.strip()
    if re.fullmatch(r"[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+\s+[A-ZÀÂÄÉÈÊËÎÏÔÙÛÜ][a-zàâäéèêëîïôùûü]+", uploader):
        return uploader

    return None


def _from_transcript(raw_transcript: str, client: Mistral) -> str | None:
    opening = " ".join(raw_transcript.split()[:300])

    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": PRESENTER_EXTRACTION_PROMPT},
            {"role": "user", "content": opening},
        ],
    )
    result = response.choices[0].message.content.strip()
    if result.lower() == "null" or not result:
        return None
    return result
