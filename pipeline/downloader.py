"""Download audio from a YouTube URL via yt-dlp.

Audio files are cached under output_dir/_cache/ so that a failed pipeline
run (e.g. API error) does not require re-downloading the video on the next
attempt.  On success the caller deletes the cache unless --audio-output
copies the file elsewhere.
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
    """Return a VideoMeta for *url*, downloading the audio only if not cached.

    The MP3 is stored at output_dir/_cache/<safe-title>.mp3.  If that file
    already exists it is reused and no network request is made for the audio.
    Metadata is always probed (cheap, no download).

    Raises RuntimeError on download failure.
    """
    cache_dir = output_dir / "_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Always probe metadata — fast, no download
    probe_opts: dict = {"quiet": True, "no_warnings": True, "nocheckcertificate": True}
    with yt_dlp.YoutubeDL(probe_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    title: str = info.get("title", "untitled")
    uploader: str = info.get("uploader") or info.get("channel") or ""
    description: str = info.get("description") or ""
    duration_seconds: int = int(info.get("duration") or 0)
    upload_date: str = info.get("upload_date") or ""

    safe_title = _safe_filename(title)
    mp3_path = cache_dir / f"{safe_title}.mp3"

    if mp3_path.exists():
        print(f"  → using cached audio: {mp3_path.name}")
    else:
        ydl_opts: dict = {
            "format": "bestaudio/best",
            "outtmpl": str(cache_dir / safe_title),
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "128",
                }
            ],
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
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
