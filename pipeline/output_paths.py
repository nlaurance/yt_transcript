"""Resolve CLI output paths (file vs directory, defaults, collision suffixes)."""

from pathlib import Path

_SUFFIXES = {".md", ".txt", ".mp3"}


def resolve_output(
    spec: str | None,
    default_dir: Path,
    stem: str,
    suffix: str,
) -> Path:
    """Return the destination path for an artifact.

    *spec* omitted → ``default_dir/<stem><suffix>`` (with _2, _3 … on collision).
    *spec* directory → same under that directory.
    *spec* file path (matching *suffix*) → that exact path (parents created).
    """
    if spec is None:
        return _unique_path(default_dir, stem, suffix)

    path = Path(spec).expanduser()
    if _is_directory_target(path, suffix):
        return _unique_path(path, stem, suffix)

    if path.suffix != suffix:
        path = path.with_suffix(suffix)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _is_directory_target(path: Path, suffix: str) -> bool:
    if path.suffix and path.suffix != suffix:
        return path.suffix not in _SUFFIXES
    if path.exists() and path.is_dir():
        return True
    # Trailing slash or no extension → treat as directory
    return path.suffix == "" or str(path).endswith("/")


def _unique_path(directory: Path, stem: str, suffix: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / f"{stem}{suffix}"
    if not candidate.exists():
        return candidate
    n = 2
    while True:
        candidate = directory / f"{stem}_{n}{suffix}"
        if not candidate.exists():
            return candidate
        n += 1
