"""Build Obsidian-compatible YAML frontmatter for the output Markdown file.

The resulting block is understood by Obsidian's metadata parser, tag browser,
and graph view out of the box.
"""

import math
from datetime import date

from pipeline.downloader import VideoMeta


def build(
    meta: VideoMeta,
    presenter: str | None,
    tags: list[str],
    language: str,
) -> str:
    """Return a YAML frontmatter block (including the opening and closing '---').

    Args:
        meta: Video metadata from the downloader.
        presenter: Speaker name, or None if unknown.
        tags: List of tag slugs from the tagger.
        language: "fr", "en", or "auto".
    """
    today = date.today().isoformat()
    duration_min = math.ceil(meta.duration_seconds / 60) if meta.duration_seconds else None

    lines = ["---"]
    lines.append(f'title: "{_escape(meta.title)}"')
    lines.append(f"date: {today}")
    lines.append(f'source: "{meta.url}"')

    if presenter:
        lines.append(f'presenter: "{_escape(presenter)}"')

    lines.append(f"language: {language}")

    if duration_min:
        lines.append(f"duration_minutes: {duration_min}")

    if tags:
        lines.append("tags:")
        for tag in tags:
            lines.append(f"  - {tag}")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _escape(text: str) -> str:
    """Escape double-quotes inside a YAML double-quoted string."""
    return text.replace('"', '\\"')
