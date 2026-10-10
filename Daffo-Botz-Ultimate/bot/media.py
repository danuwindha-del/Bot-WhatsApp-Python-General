import asyncio
import os
import signal
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED={'youtube.com','www.youtube.com','m.youtube.com','youtu.be','tiktok.com','www.tiktok.com','vm.tiktok.com','vt.tiktok.com','instagram.com','www.instagram.com'}
def validate_url(url):
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname not in ALLOWED or u.username or u.password or u.port not in (None,443):
        raise ValueError('Gunakan tautan HTTPS YouTube, TikTok, atau Instagram yang valid.')
    return url

async def process(*args,timeout=150):
    proc=await asyncio.create_subprocess_exec(*args,stdout=asyncio.subprocess.DEVNULL,stderr=asyncio.subprocess.DEVNULL,start_new_session=True)
    try:
        await asyncio.wait_for(proc.wait(),timeout)
        if proc.returncode:raise ValueError('Media tidak tersedia atau gagal dikonversi.')
    except BaseException:
        if proc.returncode is None:
            try:os.killpg(proc.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            await proc.wait()
        raise

class Downloader:
    def __init__(self):self.slots=asyncio.Semaphore(2)
    async def handle(self,ctx,url,audio=False):
        if not ctx.bot.store.config.downloader:raise ValueError('Downloader sedang dinonaktifkan.')
        validate_url(url)
        if self.slots.locked():raise ValueError('Dua unduhan sedang berjalan. Coba sebentar lagi.')
        async with self.slots:
            with tempfile.TemporaryDirectory(prefix='daffo-') as directory:
                out=Path(directory)
                # No generic extractor, no playlist, capped size/duration; network guard in worker.
                limit=ctx.bot.store.config.max_download_mb
                await process(sys.executable,'-m','bot.download_worker',url,str(out), 'audio' if audio else 'video',str(limit))
                files=[p for p in out.glob('source.*') if p.suffix not in ('.part','.ytdl')]
                if len(files)!=1:raise ValueError('Media kosong atau melebihi batas unduhan.')
                source=files[0]
                if source.stat().st_size>limit*1024*1024:raise ValueError(f'Ukuran maksimal {limit} MB.')
                target=out/('voice.ogg' if audio else 'video.mp4')
                options=['-vn','-c:a','libopus','-b:a','48k','-ar','48000','-ac','1'] if audio else ['-c:v','libx264','-preset','veryfast','-crf','24','-pix_fmt','yuv420p','-c:a','aac','-movflags','+faststart']
                await process('ffmpeg','-nostdin','-v','error','-y','-i',str(source),*options,'-t','600','-fs',str(limit)+'M',str(target))
                if not target.exists() or target.stat().st_size>=limit*1024*1024:raise ValueError(f'Hasil konversi melebihi {limit} MB.')
                data=await asyncio.to_thread(target.read_bytes)
                await ctx.bot.gate.wait(ctx.chat_key)
                if not ctx.bot.running:raise ValueError('Bot dihentikan.')
                if audio:await ctx.bot.client.send_audio(ctx.chat,data,ptt=True)
                else:await ctx.bot.client.send_video(ctx.chat,data,caption='Daffo • Media')
                ctx.bot.outgoing+=1
