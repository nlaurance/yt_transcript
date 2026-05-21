"""Generate Obsidian-compatible content tags from a processed transcript.

The LLM returns a YAML list of lowercase, hyphen-separated slugs.
We parse that list defensively so a malformed LLM response never crashes
the pipeline — at worst we get an empty tag list.
"""

import re

from mistralai.client import Mistral

from pipeline.prompts import TAGGING_PROMPT


def generate_tags(processed: str, client: Mistral) -> list[str]:
    """Return a list of tag slugs derived from *processed* transcript content."""
    response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {"role": "system", "content": TAGGING_PROMPT},
            {"role": "user", "content": processed},
        ],
    )
    raw = response.choices[0].message.content.strip()
    return _parse_yaml_list(raw)


def _parse_yaml_list(text: str) -> list[str]:
    """Extract items from a YAML-style list, tolerating minor formatting variance."""
    tags: list[str] = []
    for line in text.splitlines():
        # Match lines like "  - kubernetes" or "- ci-cd"
        match = re.match(r"^\s*-\s+(.+)$", line)
        if match:
            tag = match.group(1).strip().lower()
            # Keep only valid slug characters
            tag = re.sub(r"[^\w\-]", "", tag)
            if tag:
                tags.append(tag)
    return tags
