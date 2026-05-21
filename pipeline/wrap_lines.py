"""Wrap Markdown prose lines to a maximum width.

Paragraphs and list items are reflowed at *width* characters (default 91).
The following are passed through unchanged:
  - YAML frontmatter (between the opening and closing ---)
  - Fenced code blocks (``` or ~~~)
  - Table rows (lines starting with |)
  - Headings (lines starting with #)
  - Horizontal rules (--- / *** / ___)

Pipeline usage
--------------
    from pipeline.wrap_lines import wrap_lines
    text = wrap_lines(text, width=91)

Standalone CLI usage
--------------------
    python -m pipeline.wrap_lines <file.md>              # fix in place
    python -m pipeline.wrap_lines <file.md> --stdout     # print to stdout
    python -m pipeline.wrap_lines <file.md> --width 80   # custom width
"""

import re
import sys
import textwrap
from pathlib import Path

_DEFAULT_WIDTH = 91


def _clean_heading(text: str) -> str:
    """Normalise a heading line: remove bold markers and collapse duplicate level markers.

    '### ### Foo'  → '### Foo'
    '## **Bar**'   → '## Bar'
    """
    # Collapse duplicate heading markers, e.g. "### ### " → "### "
    text = re.sub(r"^(#{1,6})\s+#{1,6}\s+", r"\1 ", text)
    # Strip bold markers
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    return text

# Patterns that mark the start of a list item
_LIST_ITEM_RE = re.compile(r"^(\s*)([-*+]|\d+\.)\s+(.*)")
# Patterns that must never be reflowed
_HEADING_RE = re.compile(r"^#{1,6}\s")
_HRULE_RE = re.compile(r"^(\s*)([-*_])\s*(\2\s*){2,}$")
_FENCE_RE = re.compile(r"^(\s*)(```|~~~)")
_TABLE_RE = re.compile(r"^\s*\|")


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def wrap_lines(text: str, width: int = _DEFAULT_WIDTH) -> str:
    """Return *text* with prose lines wrapped at *width* characters."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []

    in_frontmatter = False
    frontmatter_closed = False
    in_code_block = False

    i = 0
    while i < len(lines):
        line = lines[i]
        raw = line.rstrip("\n")
        stripped = raw.strip()

        # ── YAML frontmatter ──────────────────────────────────────────────
        if i == 0 and stripped == "---":
            in_frontmatter = True
            result.append(line)
            i += 1
            continue

        if in_frontmatter:
            result.append(line)
            if stripped == "---" and i > 0:
                in_frontmatter = False
                frontmatter_closed = True
            i += 1
            continue

        # ── Fenced code blocks ────────────────────────────────────────────
        if _FENCE_RE.match(raw):
            in_code_block = not in_code_block
            result.append(line)
            i += 1
            continue

        if in_code_block:
            result.append(line)
            i += 1
            continue

        # ── Pass-through: table rows, headings, horizontal rules ──────────
        if _TABLE_RE.match(raw) or _HRULE_RE.match(stripped):
            result.append(line)
            i += 1
            continue

        if _HEADING_RE.match(raw):
            result.append(_clean_heading(raw) + "\n")
            i += 1
            continue

        # ── Blank lines ───────────────────────────────────────────────────
        if not stripped:
            result.append(line)
            i += 1
            continue

        # ── List items ────────────────────────────────────────────────────
        m = _LIST_ITEM_RE.match(raw)
        if m:
            indent, marker, first_content = m.group(1), m.group(2), m.group(3)
            initial_indent = indent + marker + " "
            subsequent_indent = " " * len(initial_indent)

            # Collect continuation lines (non-blank, not a new list item,
            # not a heading/table/fence) that belong to this item
            content_parts = [first_content]
            j = i + 1
            while j < len(lines):
                nxt = lines[j].rstrip("\n")
                nxt_stripped = nxt.strip()
                if (
                    not nxt_stripped
                    or _LIST_ITEM_RE.match(nxt)
                    or _HEADING_RE.match(nxt)
                    or _TABLE_RE.match(nxt)
                    or _FENCE_RE.match(nxt)
                    or _HRULE_RE.match(nxt_stripped)
                ):
                    break
                content_parts.append(nxt_stripped)
                j += 1

            wrapped = textwrap.fill(
                " ".join(content_parts),
                width=width,
                initial_indent=initial_indent,
                subsequent_indent=subsequent_indent,
            )
            result.append(wrapped + "\n")
            i = j
            continue

        # ── Regular paragraph text ────────────────────────────────────────
        # Collect consecutive paragraph lines into one block to reflow
        para_parts: list[str] = []
        j = i
        while j < len(lines):
            nxt = lines[j].rstrip("\n")
            nxt_stripped = nxt.strip()
            if (
                not nxt_stripped
                or _LIST_ITEM_RE.match(nxt)
                or _HEADING_RE.match(nxt)
                or _TABLE_RE.match(nxt)
                or _FENCE_RE.match(nxt)
                or _HRULE_RE.match(nxt_stripped)
            ):
                break
            para_parts.append(nxt_stripped)
            j += 1

        if para_parts:
            wrapped = textwrap.fill(" ".join(para_parts), width=width)
            result.append(wrapped + "\n")
            i = j
        else:
            result.append(line)
            i += 1

    return "".join(result)


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------

def _fix_file(path: str, to_stdout: bool, width: int) -> int:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"error reading {path}: {e}", file=sys.stderr)
        return 1

    fixed = wrap_lines(text, width=width)

    if to_stdout:
        sys.stdout.write(fixed)
    else:
        try:
            Path(path).write_text(fixed, encoding="utf-8")
            print(f"wrapped: {path}")
        except OSError as e:
            print(f"error writing {path}: {e}", file=sys.stderr)
            return 1

    return 0


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    to_stdout = "--stdout" in args
    width = _DEFAULT_WIDTH

    if "--width" in args:
        idx = args.index("--width")
        try:
            width = int(args[idx + 1])
            args = [a for j, a in enumerate(args) if j not in (idx, idx + 1)]
        except (IndexError, ValueError):
            print("error: --width requires an integer argument", file=sys.stderr)
            sys.exit(1)

    paths = [a for a in args if not a.startswith("--")]

    if not paths:
        print("error: no file paths provided", file=sys.stderr)
        sys.exit(1)

    exit_code = 0
    for path in paths:
        exit_code |= _fix_file(path, to_stdout, width)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
