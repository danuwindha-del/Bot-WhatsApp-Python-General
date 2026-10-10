from __future__ import annotations

import glob
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from yt_dlp import YoutubeDL

from ..utils import validate_public_http_url


class DownloaderFeature:
    def __init__(self, router, settings):
        self.settings = settings
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="daffo-download")
        router.add("dl", self.video)
        router.add("mp3", self.audio)

    def video(self, ctx, args: str) -> None:
        self._submit(ctx, args, audio=False)

    def audio(self, ctx, args: str) -> None:
        self._submit(ctx, args, audio=True)

    def _submit(self, ctx, url: str, audio: bool) -> None:
        if not url:
            raise ValueError("Masukkan URL media.")
        validate_public_http_url(url)
        ctx.reply("⏳ Memproses media…")
        self.pool.submit(self._job, ctx, url, audio)

    def _job(self, ctx, url: str, audio: bool) -> None:
        token = uuid.uuid4().hex
        base = Path("downloads") / token
        pattern = str(base) + ".*"
        try:
            opts = {
                "outtmpl": str(base) + ".%(ext)s",
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "max_filesize": self.settings.max_download_mb * 1024 * 1024,
                "restrictfilenames": True,
            }
            if audio:
                opts.update(
                    {
                        "format": "bestaudio/best",
                        "postprocessors": [
                            {
                                "key": "FFmpegExtractAudio",
                                "preferredcodec": "mp3",
                                "preferredquality": "128",
                            }
                        ],
                    }
                )
            else:
                opts.update(
                    {
                        "format": "bv*[height<=720]+ba/b[height<=720]/best",
                        "merge_output_format": "mp4",
                    }
                )
            with YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = (info or {}).get("title", "Media")

            files = [Path(p) for p in glob.glob(pattern) if Path(p).is_file()]
            if not files:
                raise RuntimeError("File hasil unduhan tidak ditemukan.")
            output = max(files, key=lambda p: p.stat().st_mtime)
            if output.stat().st_size > self.settings.max_download_mb * 1024 * 1024:
                raise RuntimeError(f"Ukuran file melebihi batas {self.settings.max_download_mb} MB.")

            if audio:
                ctx.client.send_audio(ctx.chat, str(output))
                ctx.client.send_message(ctx.chat, f"🎵 {title}")
            elif output.suffix.lower() in {".mp4", ".mov", ".mkv", ".webm"}:
                ctx.client.send_video(ctx.chat, str(output), caption=f"🎬 {title}")
            else:
                ctx.client.send_document(ctx.chat, str(output), filename=output.name, caption=title)
        except Exception as exc:
            ctx.send(f"❌ Downloader gagal: {exc}")
        finally:
            for path in glob.glob(pattern):
                try:
                    os.remove(path)
                except OSError:
                    pass
