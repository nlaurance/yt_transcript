"""Align Markdown tables for human reading.

All pipe characters are made to line up vertically; cell content is padded
with trailing spaces; separator dashes span the full column width.

Core logic adapted from the markdown-tables skill (fix_md_tables.py).

Pipeline usage
--------------
    from pipeline.format_tables import format_tables
    text = format_tables(text)

Standalone CLI usage
--------------------
    python -m pipeline.format_tables <file.md>            # fix in place
    python -m pipeline.format_tables <file.md> --stdout   # print to stdout
    python -m pipeline.format_tables <f1.md> <f2.md>      # fix multiple files
"""

import re
import sys
from pathlib import Path


def _strip_bold(text: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _parse_row(line: str) -> list[str]:
    s = line.rstrip("\n")
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return s.split("|")


def _is_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in cells)


def _fix_table_block(block: list[str]) -> list[str]:
    rows = [_parse_row(ln) for ln in block]
    n_cols = max(len(r) for r in rows)

    for row in rows:
        while len(row) < n_cols:
            row.append("")

    col_widths = [0] * n_cols
    for row in rows:
        if _is_separator(row):
            continue
        for col, cell in enumerate(row):
            col_widths[col] = max(col_widths[col], len(cell.strip()))

    col_widths = [max(w, 3) for w in col_widths]

    # Index of the first non-separator row (the header)
    header_idx = next(
        (idx for idx, row in enumerate(rows) if not _is_separator(row)), None
    )

    fixed = []
    for idx, row in enumerate(rows):
        if _is_separator(row):
            cells = ["-" * (col_widths[col] + 2) for col in range(n_cols)]
            fixed.append("|" + "|".join(cells) + "|\n")
        else:
            is_header = idx == header_idx
            cells = [
                _strip_bold(row[col].strip()).ljust(col_widths[col]) if is_header
                else row[col].strip().ljust(col_widths[col])
                for col in range(n_cols)
            ]
            fixed.append("| " + " | ".join(cells) + " |\n")

    return fixed


def format_tables(text: str) -> str:
    """Return *text* with all Markdown tables reformatted for alignment."""
    lines = text.splitlines(keepends=True)
    result: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("|"):
            block: list[str] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                block.append(lines[i])
                i += 1
            result.extend(_fix_table_block(block))
        else:
            result.append(lines[i])
            i += 1
    return "".join(result)


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------

def _fix_file(path: str, to_stdout: bool) -> int:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as e:
        print(f"error reading {path}: {e}", file=sys.stderr)
        return 1

    fixed = format_tables(text)

    if to_stdout:
        sys.stdout.write(fixed)
    else:
        try:
            Path(path).write_text(fixed, encoding="utf-8")
            print(f"fixed: {path}")
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
    paths = [a for a in args if a != "--stdout"]

    if not paths:
        print("error: no file paths provided", file=sys.stderr)
        sys.exit(1)

    exit_code = 0
    for path in paths:
        exit_code |= _fix_file(path, to_stdout)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
