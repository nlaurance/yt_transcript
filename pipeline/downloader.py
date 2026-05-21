"""Download audio from a YouTube URL via yt-dlp.

Returns a VideoMeta dataclass with the MP3 path and video metadata
(title, uploader, description, duration, upload date) for use by the
presenter-extraction and frontmatter modules.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import yt_dlp


@dataclass
class VideoMeta:
    mp3_path: Path
    title: str
    url: str
    uploader: str
    description: str
    duration_seconds: int
    upload_date: str  # YYYYMMDD as returned by yt-dlp


def download_audio(url: str, output_dir: Path) -> VideoMeta:
    """Download the audio track of a YouTube video as MP3.

    The MP3 is written to *output_dir* under a sanitised filename derived from
    the video title.  Caller is responsible for deleting the file afterwards.

    Raises RuntimeError on download failure.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Probe metadata first without downloading
    probe_opts: dict = {"quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title: str = info.get("title", "untitled")
    uploader: str = info.get("uploader") or info.get("channel") or ""
    description: str = info.get("description") or ""
    duration_seconds: int = int(info.get("duration") or 0)
    upload_date: str = info.get("upload_date") or ""

    safe_title = _safe_filename(title)
    mp3_path = output_dir / f"{safe_title}.mp3"

    ydl_opts: dict = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / safe_title),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "128",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ret = ydl.download([url])

    if ret != 0:
        raise RuntimeError(f"yt-dlp exited with code {ret} for URL: {url}")

    if not mp3_path.exists():
        raise RuntimeError(f"Expected MP3 not found at {mp3_path}")

    return VideoMeta(
        mp3_path=mp3_path,
        title=title,
        url=url,
        uploader=uploader,
        description=description,
        duration_seconds=duration_seconds,
        upload_date=upload_date,
    )


def _safe_filename(title: str) -> str:
    """Return a filesystem-safe version of a video title."""
    safe = re.sub(r'[^\w\s\-]', '', title)
    safe = re.sub(r'\s+', '_', safe.strip())
    return safe[:80] or "video"
