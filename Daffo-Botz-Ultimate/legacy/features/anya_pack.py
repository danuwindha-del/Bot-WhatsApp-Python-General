from __future__ import annotations

import ast
import hashlib
import html
import io
import json
import math
import os
import random
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from PIL import Image, ImageFilter, ImageOps

from ..utils import media_message, target_jids_from_event


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "anya"


@dataclass
class QuizSession:
    answer: str | list[str]
    kind: str


class AnyaGameFeature:
    """Port of Anya's local-data quiz/game pack.

    Uses the original JSON question banks supplied by the uploaded Anya project.
    This keeps the questions available offline while using Daffo-Botz's Python router.
    """

    def __init__(self, router):
        self.sessions: dict[str, QuizSession] = {}
        self.data_cache={}
        self.lock = threading.RLock()
        self.router = router

        commands = {
            "susunkata": self.susunkata,
            "tebakbenda": self.tebakbenda,
            "tebakgambar": self.tebakgambar,
            "tebakbuah": self.tebakbuah,
            "tebaklogo": self.tebaklogo,
            "tebaklagu": self.tebaklagu,
            "tebaklirik": self.tebaklirik,
            "tebakkimia": self.tebakkimia,
            "siapakahaku": self.siapakahaku,
            "family100": self.family100,
            "tebakbendera": self.tebakbendera,
            "tebakgame": self.tebakgame,
            "tebaktebakan": self.tebaktebakan,
            "tebakanml": self.tebakanml,
            "jawab": self.answer,
            "nyerah": self.give_up,
            "dadu": self.dice,
            "slot": self.slot,
            "tebakwarna": self.tebakwarna,
            "hangman": self.hangman,
        }
        for name, handler in commands.items():
            router.add(name, handler)

    def _load(self, name: str):
        p = DATA_DIR / f"{name}.json"
        if not p.exists():
            raise ValueError(f"Database game {name} tidak tersedia.")
        if name not in self.data_cache:self.data_cache[name]=json.loads(p.read_text(encoding="utf-8"))
        return self.data_cache[name]

    def _save(self, ctx, answer, kind):
        with self.lock:
            getattr(self,"other_sessions",{}).pop(ctx.chat_key,None)
            if len(self.sessions)>=700:self.sessions.pop(next(iter(self.sessions)))
            self.sessions[ctx.chat_key] = QuizSession(answer, kind)

    def _text_quiz(self, ctx, db: str, question_keys, answer_keys, title: str):
        data = self._load(db)
        item = random.choice(data)
        question = next((item.get(k) for k in question_keys if item.get(k)), None)
        answer = next((item.get(k) for k in answer_keys if item.get(k)), None)
        if question is None or answer is None:
            raise ValueError("Format database game tidak dikenali.")
        self._save(ctx, answer, db)
        ctx.reply(f"🎮 *{title}*\n\n{question}\n\nJawab: `.jawab <jawaban>`\nMenyerah: `.nyerah`")

    def susunkata(self, ctx, _args):
        data = self._load("susunkata")
        item = random.choice(data)
        q = item.get("soal", "")
        a = item.get("jawaban", "")
        tipe = item.get("tipe", "Umum")
        self._save(ctx, a, "susunkata")
        ctx.reply(f"🔤 *SUSUN KATA*\nKategori: {tipe}\nHuruf: `{q}`\n\nJawab: `.jawab <kata>`")

    def tebakbenda(self, ctx, _args):
        self._text_quiz(ctx, "tebakbenda", ("question", "soal"), ("answer", "jawaban"), "TEBAK BENDA")

    def tebakbuah(self, ctx, _args):
        self._text_quiz(ctx, "tebakbuah", ("soal", "question"), ("jawaban", "answer"), "TEBAK BUAH")

    def tebaklirik(self, ctx, _args):
        self._text_quiz(ctx, "tebaklirik", ("soal",), ("jawaban",), "TEBAK LIRIK")

    def siapakahaku(self, ctx, _args):
        self._text_quiz(ctx, "siapakahaku", ("soal",), ("jawaban",), "SIAPAKAH AKU")

    def tebaktebakan(self, ctx, _args):
        self._text_quiz(ctx, "tebaktebakan", ("soal", "question"), ("jawaban", "answer"), "TEBAK-TEBAKAN")

    def tebakanml(self, ctx, _args):
        self._text_quiz(ctx, "tebakanml", ("soal", "question"), ("jawaban", "answer"), "TEBAKAN ML")

    def tebakgame(self, ctx, _args):
        item=random.choice(self._load('tebakgame'))
        self._save(ctx,item['jawaban'],'tebakgame')
        ctx.reply('🎮 Tebak game pada gambar berikut:\n'+item['img']+'\nJawab: .jawab nama game')

    def tebakkimia(self, ctx, _args):
        data = self._load("tebakkimia")
        item = random.choice(data)
        if random.choice((True, False)):
            q, a = f"Apa lambang unsur *{item['unsur']}*?", item["lambang"]
        else:
            q, a = f"Unsur apakah yang memiliki lambang *{item['lambang']}*?", item["unsur"]
        self._save(ctx, a, "tebakkimia")
        ctx.reply(f"🧪 *TEBAK KIMIA*\n\n{q}\n\nJawab: `.jawab <jawaban>`")

    def _download_media(self, url: str, suffix: str) -> Path:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 Daffo-Botz"})
        with urlopen(req, timeout=15) as r:
            data = r.read(12 * 1024 * 1024)
        fd, name = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        p = Path(name)
        p.write_bytes(data)
        return p

    def tebakgambar(self, ctx, _args):
        item = random.choice(self._load("tebakgambar"))
        self._save(ctx, item["jawaban"], "tebakgambar")
        try:
            p = self._download_media(item["img"], ".jpg")
            try:
                ctx.client.send_image(ctx.chat, str(p), caption="🖼️ *TEBAK GAMBAR*\nJawab: `.jawab <jawaban>`")
            finally:
                p.unlink(missing_ok=True)
        except Exception:
            ctx.reply(f"🖼️ *TEBAK GAMBAR*\nPetunjuk: {item.get('deskripsi','-')}\nJawab: `.jawab <jawaban>`")

    def tebaklogo(self, ctx, _args):
        item = random.choice(self._load("tebaklogo"))
        self._save(ctx, item["jawaban"], "tebaklogo")
        caption = f"🏷️ *TEBAK LOGO*\nPetunjuk: {item.get('deskripsi','-')}\nJawab: `.jawab <jawaban>`"
        try:
            p = self._download_media(item["img"], ".png")
            try:
                ctx.client.send_image(ctx.chat, str(p), caption=caption)
            finally:
                p.unlink(missing_ok=True)
        except Exception:
            ctx.reply(caption)

    def tebaklagu(self, ctx, _args):
        item = random.choice(self._load("tebaklagu"))
        self._save(ctx, item["judul"], "tebaklagu")
        try:
            p = self._download_media(item["lagu"], ".mp3")
            try:
                ctx.client.send_audio(ctx.chat, str(p))
                ctx.send(f"🎵 *TEBAK LAGU*\nArtis: {item.get('artis','?')}\nJawab: `.jawab <judul>`")
            finally:
                p.unlink(missing_ok=True)
        except Exception:
            ctx.reply(f"🎵 *TEBAK LAGU*\nArtis: {item.get('artis','?')}\nAudio gagal dimuat. Coba game lain.")

    def family100(self, ctx, _args):
        item = random.choice(self._load("family100"))
        self._save(ctx, item["jawaban"], "family100")
        ctx.reply(f"👨‍👩‍👧‍👦 *FAMILY 100*\n\n{item['soal']}\nAda {len(item['jawaban'])} jawaban.\nKirim `.jawab <jawaban>` satu per satu.")

    def tebakbendera(self, ctx, _args):
        item=random.choice(self._load('tebakbendera'))
        code=item['flag'].upper()
        flag=''.join(chr(127397+ord(c)) for c in code) if len(code)==2 else item['img']
        self._save(ctx,item['name'],'tebakbendera')
        ctx.reply('🏳️ Negara apakah ini? '+flag+'\nJawab: .jawab nama negara')

    def tebakwarna(self, ctx, _args):
        colors = [("Merah", "🔴"), ("Biru", "🔵"), ("Hijau", "🟢"), ("Kuning", "🟡"), ("Ungu", "🟣"), ("Oranye", "🟠")]
        answer, emoji = random.choice(colors)
        self._save(ctx, answer, "tebakwarna")
        ctx.reply(f"🎨 *TEBAK WARNA*\n\nWarna apakah ini? {emoji}\nJawab: `.jawab <warna>`")

    def hangman(self, ctx, _args):
        words = ["python", "whatsapp", "neonize", "komputer", "algoritma", "indonesia", "developer"]
        answer = random.choice(words)
        self._save(ctx, answer, "hangman")
        ctx.reply("🪢 *HANGMAN*\n\n" + " ".join("_" for _ in answer) + "\nJawab: `.jawab <kata>`")

    def dice(self, ctx, _args):
        ctx.reply(f"🎲 Dadu: *{random.randint(1, 6)}*")

    def slot(self, ctx, _args):
        icons = ["🍒", "🍋", "🍇", "⭐", "💎"]
        roll = [random.choice(icons) for _ in range(3)]
        win = len(set(roll)) == 1
        ctx.reply(f"🎰 | {' | '.join(roll)} |\n" + ("🎉 *JACKPOT!*" if win else "Coba lagi!"))

    @staticmethod
    def _norm(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", s.casefold())

    def answer(self, ctx, args):
        if not args:
            raise ValueError("Masukkan jawaban.")
        with self.lock:
            ses = self.sessions.get(ctx.chat_key)
        if not ses:
            raise ValueError("Tidak ada game Daffo yang aktif.")
        cand = self._norm(args)
        if isinstance(ses.answer, list):
            answers = [str(x) for x in ses.answer]
            hit = next((x for x in answers if self._norm(x) == cand), None)
            if hit:
                answers.remove(hit)
                if answers:
                    self._save(ctx, answers, ses.kind)
                    ctx.reply(f"✅ Benar: *{hit}*. Tersisa {len(answers)} jawaban.")
                else:
                    with self.lock: self.sessions.pop(ctx.chat_key, None)
                    ctx.reply("🎉 *SEMUA JAWABAN BERHASIL DITEMUKAN!*")
            else:
                ctx.reply("❌ Belum tepat.")
            return
        if cand == self._norm(str(ses.answer)):
            with self.lock: self.sessions.pop(ctx.chat_key, None)
            ctx.reply(f"✅ *BENAR!* Jawaban: *{ses.answer}* 🎉")
        else:
            ctx.reply("❌ Belum tepat. Coba lagi!")

    def give_up(self, ctx, _args):
        with self.lock:
            ses = self.sessions.pop(ctx.chat_key, None)
        if not ses:
            raise ValueError("Tidak ada game aktif.")
        ans = ", ".join(map(str, ses.answer)) if isinstance(ses.answer, list) else str(ses.answer)
        ctx.reply(f"🏳️ Menyerah. Jawabannya: *{ans}*")


class AnyaFunFeature:
    TRUTHS = [
        "Apa hal paling memalukan yang pernah kamu lakukan?",
        "Siapa orang terakhir yang kamu stalking?",
        "Apa kebiasaanmu yang paling aneh?",
        "Apa ketakutan terbesar yang jarang kamu ceritakan?",
        "Pernah bohong ke teman dekat? Tentang apa?",
    ]
    DARES = [
        "Kirim voice note menyanyikan 10 detik lagu favoritmu.",
        "Ganti foto profil selama 10 menit dengan gambar lucu.",
        "Kirim satu pujian tulus ke anggota grup.",
        "Buat pantun spontan tentang grup ini.",
        "Gunakan emoji 😎 di setiap pesan selama 5 menit.",
    ]

    def __init__(self, router):
        mapping = {
            "truth": self.truth, "dare": self.dare, "carabalikan": self.reverse,
            "pilih": self.choose, "angka": self.number, "cekiq": self.iq,
            "cekcantik": self.cantik, "cantikcek": self.cantik,
            "gantengcek": self.ganteng, "ceksifat": self.sifat,
            "cekkhodam": self.khodam, "stress": self.stress,
            "quotebucin": self.bucin, "sadboy": self.sad,
            "jadian": self.jadian, "dimanakah": self.where,
        }
        for k, v in mapping.items(): router.add(k, v)

    def _score(self, ctx, salt: str, maxv=100):
        raw = f"{ctx.sender_key}:{salt}".encode()
        return int(hashlib.sha256(raw).hexdigest()[:8], 16) % (maxv + 1)

    def truth(self, ctx, _): ctx.reply("🫣 *TRUTH*\n" + random.choice(self.TRUTHS))
    def dare(self, ctx, _): ctx.reply("🔥 *DARE*\n" + random.choice(self.DARES))
    def reverse(self, ctx, args):
        if not args: raise ValueError("Masukkan teks.")
        ctx.reply(args[::-1])
    def choose(self, ctx, args):
        choices=[x.strip() for x in re.split(r"[|,]", args) if x.strip()]
        if len(choices)<2: raise ValueError("Contoh: .pilih nasi | mie")
        ctx.reply(f"🤔 Aku pilih: *{random.choice(choices)}*")
    def number(self, ctx, args):
        try: hi=max(1,min(int(args or 100),1_000_000))
        except: hi=100
        ctx.reply(f"🔢 Angka acak: *{random.randint(1,hi)}*")
    def iq(self, ctx, _): ctx.reply(f"🧠 IQ versi game: *{70 + self._score(ctx,'iq',90)}*\n_(sekadar hiburan)_")
    def cantik(self, ctx, _): ctx.reply(f"✨ Tingkat cantik versi game: *{self._score(ctx,'cantik')}%*\n_(sekadar hiburan)_")
    def ganteng(self, ctx, _): ctx.reply(f"😎 Tingkat ganteng versi game: *{self._score(ctx,'ganteng')}%*\n_(sekadar hiburan)_")
    def stress(self, ctx, _): ctx.reply(f"🌀 Meter stress versi game: *{self._score(ctx,'stress')}%*\n_(sekadar hiburan)_")
    def sifat(self, ctx, _):
        opts=["ramah", "ambisius", "santai", "kreatif", "penasaran", "humoris", "teliti", "berani"]
        rnd=random.Random(self._score(ctx,'sifat',2**16)); ctx.reply("🪞 Sifat versi game: *" + ", ".join(rnd.sample(opts,3)) + "*")
    def khodam(self, ctx, _):
        opts=["Kucing Oren", "Naga WiFi", "Macan Rebahan", "Elang Kopi", "Panda Deadline", "Tidak terdeteksi"]
        ctx.reply(f"🔮 Khodam versi hiburan: *{random.choice(opts)}*")
    def bucin(self, ctx, _):
        q=["Kalau rindu punya alamat, mungkin semuanya menuju kamu.", "Aku tidak butuh peta, selama tujuan akhirnya kamu.", "Bukan sinyal yang hilang, cuma kamu yang lama membalas."]
        ctx.reply("💗 " + random.choice(q))
    def sad(self, ctx, _):
        q=["Tidak semua yang dekat memilih menetap.", "Kadang yang perlu disembuhkan bukan luka, tetapi harapan.", "Ada cerita yang selesai tanpa sempat diberi penutup."]
        ctx.reply("🌧️ " + random.choice(q))
    def jadian(self, ctx, _): ctx.reply(f"💞 Meter kecocokan versi game: *{self._score(ctx,'jadian')}%*")
    def where(self, ctx, args):
        if not args: raise ValueError("Masukkan pertanyaan. Contoh: .dimanakah jodohku")
        ctx.reply("📍 Jawaban random: *" + random.choice(["dekat, tapi belum sadar", "di tempat yang tidak kamu duga", "masih sibuk dengan hidupnya", "mungkin sudah ada di kontakmu"]) + "*")


class AnyaInfoFeature:
    def __init__(self, router, settings, started_at: float):
        self.router=router; self.settings=settings; self.started_at=started_at
        for name in ("ping","speed","runtime","statusbot","botinfo","stats","totalfitur","totaluser","tes"):
            router.add(name, self.info)
        router.add("owner", self.owner, aliases=("creator",))
        router.add("script", self.script, aliases=("sc",))

    def info(self, ctx, _args):
        uptime=int(time.time()-self.started_at)
        h, rem=divmod(uptime,3600); m,s=divmod(rem,60)
        ctx.reply(
            f"🤖 *{self.settings.bot_name}*\n"
            f"✅ Status: Online\n"
            f"⏱️ Runtime: {h:02}:{m:02}:{s:02}\n"
            f"🧩 Commands: {self.router.command_count}\n"
            f"🐍 Python: {os.sys.version.split()[0]}"
        )
    def owner(self, ctx, _):
        owners=sorted(self.settings.owner_numbers)
        ctx.reply("👑 Dibuat oleh *Lord Daffo* • 085648175452\nAdmin bot: " + (", ".join("+"+x for x in owners) if owners else "belum diatur di dashboard"))
    def script(self, ctx, _): ctx.reply("🧩 *Daffo-Botz Python*\nCore: Neonize/whatsmeow\nDaffo feature pack: aktif")


class AnyaInternetFeature:
    def __init__(self, router):
        router.add("wiki", self.wikipedia, aliases=("wikipedia",))
        router.add("kbbi", self.kbbi)
        router.add("translate", self.translate, aliases=("tr",))
        router.add("doa", self.doa)

    def wikipedia(self, ctx, args):
        if not args: raise ValueError("Contoh: .wiki Indonesia")
        url="https://id.wikipedia.org/api/rest_v1/page/summary/"+quote(args.replace(" ","_"), safe="")
        try:
            req=Request(url,headers={"User-Agent":"Daffo-Botz/2.0"})
            with urlopen(req,timeout=10) as r: d=json.loads(r.read().decode())
            extract=d.get("extract") or "Ringkasan tidak ditemukan."
            ctx.reply(f"📚 *WIKIPEDIA*\n\n{extract[:3500]}")
        except Exception as e: raise ValueError(f"Wikipedia gagal: {e}")

    def kbbi(self, ctx, args):
        if not args: raise ValueError("Contoh: .kbbi algoritma")
        p=DATA_DIR/"kbbi.json"
        data=json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        q=args.strip().casefold()
        found=None
        if isinstance(data,dict): found=data.get(q) or data.get(args.strip())
        elif isinstance(data,list):
            found=next((x for x in data if (x.casefold() if isinstance(x,str) else str(x.get('word',x.get('kata',''))).casefold())==q),None)
            if isinstance(found,str):
                ctx.reply('📖 Kata *'+found+'* ditemukan dalam daftar kata lokal. Dataset ini tidak memuat definisi.');return
        if found is None: raise ValueError("Kata tidak ditemukan di database KBBI lokal.")
        ctx.reply("📖 *KBBI*\n\n"+str(found)[:3500])

    def translate(self, ctx, args):
        if not args: raise ValueError("Contoh: .translate en|selamat pagi")
        if "|" in args: target,text=[x.strip() for x in args.split("|",1)]
        else: target,text="en",args
        params=urlencode({"q":text,"langpair":f"id|{target}"})
        try:
            req=Request("https://api.mymemory.translated.net/get?"+params,headers={"User-Agent":"Daffo-Botz/2.0"})
            with urlopen(req,timeout=10) as r: d=json.loads(r.read().decode())
            out=d.get("responseData",{}).get("translatedText")
            if not out: raise RuntimeError("hasil kosong")
            ctx.reply(f"🌐 *TRANSLATE → {target.upper()}*\n\n{html.unescape(out)}")
        except Exception as e: raise ValueError(f"Translate gagal: {e}")

    def doa(self, ctx, args):
        prayers={
            "makan": "Bismillāh. Ya Allah, berkahilah rezeki yang Engkau berikan kepada kami.",
            "tidur": "Bismika Allāhumma ahyā wa bismika amūt.",
            "bangun": "Alhamdulillāhilladzī ahyānā ba‘da mā amātanā wa ilaihin-nusyūr.",
            "belajar": "Rabbi zidnī ‘ilmā warzuqnī fahmā.",
        }
        if not args:
            ctx.reply("🤲 Doa tersedia: "+", ".join(prayers)); return
        q=args.casefold(); hit=next((v for k,v in prayers.items() if k in q),None)
        if not hit: raise ValueError("Doa belum ada. Pilih: "+", ".join(prayers))
        ctx.reply("🤲 *DOA*\n\n"+hit)


class AnyaToolsFeature:
    def __init__(self, router):
        router.add("qrcode", self.qrcode, aliases=("barcode",))
        router.add("kalkulator", self.calc, aliases=("calc",))
        router.add("resize", self.resize)
        router.add("blur", self.blur)
        router.add("toimg", self.to_image)
        router.add("tomp3", self.to_mp3)
        router.add("compress", self.compress)

    def qrcode(self, ctx, args):
        if not args: raise ValueError("Contoh: .qrcode https://example.com")
        import qrcode
        img=qrcode.make(args)
        with tempfile.NamedTemporaryFile(suffix=".png",delete=False) as f: path=f.name
        try:
            img.save(path); ctx.client.send_image(ctx.chat,path,caption="🔳 QR Code")
        finally: Path(path).unlink(missing_ok=True)

    def calc(self, ctx, args):
        from bot.calculator import calculate
        ctx.reply('🧮 Hasil: '+calculate(args))

    def _get_image(self,ctx):
        msg=media_message(ctx.event)
        if msg is None: raise ValueError("Kirim/reply gambar terlebih dahulu.")
        data=ctx.client.download_any(msg)
        if not data: raise ValueError("Media gagal diunduh.")
        try: return Image.open(io.BytesIO(data)).convert("RGB")
        except: raise ValueError("Media bukan gambar yang valid.")

    def _send_img(self,ctx,img,caption):
        with tempfile.NamedTemporaryFile(suffix=".jpg",delete=False) as f: p=Path(f.name)
        try: img.save(p,"JPEG",quality=88,optimize=True); ctx.client.send_image(ctx.chat,str(p),caption=caption)
        finally: p.unlink(missing_ok=True)

    def resize(self,ctx,args):
        m=re.search(r"(\d+)\s*[x ]\s*(\d+)",args)
        if not m: raise ValueError("Contoh: reply gambar lalu .resize 512x512")
        w,h=map(int,m.groups()); w=max(32,min(w,2048)); h=max(32,min(h,2048))
        self._send_img(ctx,self._get_image(ctx).resize((w,h),Image.Resampling.LANCZOS),f"🖼️ Resize {w}×{h}")
    def blur(self,ctx,args):
        try: radius=max(1,min(float(args or 8),40))
        except: radius=8
        self._send_img(ctx,self._get_image(ctx).filter(ImageFilter.GaussianBlur(radius)),"🌫️ Blur")
    def to_image(self,ctx,_): self._send_img(ctx,self._get_image(ctx),"🖼️ Converted image")
    def compress(self,ctx,_):
        img=self._get_image(ctx); img.thumbnail((1280,1280),Image.Resampling.LANCZOS); self._send_img(ctx,img,"🗜️ Compressed")
    def to_mp3(self,ctx,_):
        msg=media_message(ctx.event)
        if msg is None: raise ValueError("Reply video/audio lalu .tomp3")
        data=ctx.client.download_any(msg)
        if not data: raise ValueError("Media gagal diunduh.")
        with tempfile.TemporaryDirectory() as td:
            src=Path(td)/"input.bin"; out=Path(td)/"audio.mp3"; src.write_bytes(data)
            cp=subprocess.run(["ffmpeg","-y","-i",str(src),"-vn","-b:a","128k",str(out)],capture_output=True,timeout=90)
            if cp.returncode!=0 or not out.exists(): raise ValueError("FFmpeg gagal mengubah media ke MP3.")
            ctx.client.send_audio(ctx.chat,str(out))


class AnyaGroupExtrasFeature:
    def __init__(self, router, permissions):
        self.permissions=permissions
        router.add("tagall",self.tagall)
        router.add("kickme",self.kickme)
        router.add("adminlist",self.adminlist)
        router.add("linkgc",self.link,aliases=("linkgrup",))
        router.add("revoke",self.revoke)

    def tagall(self,ctx,args):
        self.permissions.require_group(ctx)
        info=ctx.client.get_group_info(ctx.chat)
        jids=[getattr(p,"JID",None) for p in getattr(info,"Participants",[]) or []]
        jids=[j for j in jids if j is not None and getattr(j,"User","")]
        text=(args.strip()+"\n\n" if args.strip() else "📢 *TAG ALL*\n\n") + " ".join(f"@{j.User}" for j in jids)
        ctx.client.send_message(ctx.chat,text,ghost_mentions=" ".join(f"@{j.User}" for j in jids),mentions_are_lids=all(getattr(j,"Server","")=="lid" for j in jids))

    def kickme(self,ctx,_):
        self.permissions.require_group(ctx)
        from neonize.utils.enum import ParticipantChange
        ctx.client.update_group_participants(ctx.chat,[ctx.sender],ParticipantChange.REMOVE)

    def adminlist(self,ctx,_):
        self.permissions.require_group(ctx)
        info=ctx.client.get_group_info(ctx.chat); admins=[]
        for p in getattr(info,"Participants",[]) or []:
            if getattr(p,"IsAdmin",False) or getattr(p,"IsSuperAdmin",False):
                j=getattr(p,"JID",None)
                if j and getattr(j,"User",""): admins.append(f"• +{j.User}")
        ctx.reply("👑 *ADMIN GROUP*\n"+("\n".join(admins) if admins else "Tidak terdeteksi."))

    def link(self,ctx,_):
        self.permissions.require_group(ctx)
        fn=getattr(ctx.client,"get_group_invite_link",None)
        if not fn: raise ValueError("Versi Neonize ini tidak menyediakan get_group_invite_link.")
        ctx.reply("🔗 *LINK GROUP*\n"+str(fn(ctx.chat)))

    def revoke(self,ctx,_):
        self.permissions.require_admin(ctx)
        result=ctx.client.get_group_invite_link(ctx.chat,revoke=True)
        ctx.reply('✅ Link undangan diperbarui.\n'+str(result))


class AnyaEconomyFeature:
    """Lightweight Python economy/RPG compatibility layer.

    It intentionally avoids gambling-style commands from the source pack. The safe
    progression commands share one SQLite-backed profile per WhatsApp account.
    """
    def __init__(self, router, store):
        self.store=store
        self._ensure_schema()
        mapping={
            "daftar":self.register,"register":self.register,"unreg":self.unregister,
            "profile":self.profile,"profil":self.profile,"inventory":self.profile,"inv":self.profile,"merpg":self.profile,
            "harian":self.daily,"claim":self.daily,"kerja":self.work,"nguli":self.work,
            "mining":self.activity,"mancing":self.activity,"berburu":self.activity,"hunt":self.activity,
            "mulung":self.activity,"nebang":self.activity,"berkebun":self.activity,"warnet":self.activity,
            "warteg":self.activity,"endorse":self.activity,"fyp":self.activity,"petualang":self.activity,
            "deposit":self.deposit,"withdraw":self.withdraw,"bank":self.profile,"atm":self.profile,
            "leaderboard":self.leaderboard,"lb":self.leaderboard,"rank":self.leaderboard,"levelup":self.levelup,
            "limit":self.limit,
        }
        for k,v in mapping.items(): router.add(k,v)

    def _ensure_schema(self):
        with self.store._lock, self.store._conn:
            self.store._conn.executescript('''
            CREATE TABLE IF NOT EXISTS anya_users(
              user_jid TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT '', money INTEGER NOT NULL DEFAULT 1000,
              bank INTEGER NOT NULL DEFAULT 0, exp INTEGER NOT NULL DEFAULT 0, level INTEGER NOT NULL DEFAULT 1,
              daily_at INTEGER NOT NULL DEFAULT 0, work_at INTEGER NOT NULL DEFAULT 0
            );
            ''')
    def _row(self,ctx,create=True):
        with self.store._lock,self.store._conn:
            if create:self.store._conn.execute("INSERT OR IGNORE INTO anya_users(user_jid,name) VALUES(?,?)",(ctx.sender_key,ctx.sender_number))
            return self.store._conn.execute("SELECT * FROM anya_users WHERE user_jid=?",(ctx.sender_key,)).fetchone()
    def register(self,ctx,args):
        self._row(ctx); name=args.strip() or ctx.sender_number
        with self.store._lock,self.store._conn:self.store._conn.execute("UPDATE anya_users SET name=? WHERE user_jid=?",(name,ctx.sender_key))
        ctx.reply(f"✅ RPG/Economy terdaftar sebagai *{name}*.")
    def unregister(self,ctx,_):
        with self.store._lock,self.store._conn:self.store._conn.execute("DELETE FROM anya_users WHERE user_jid=?",(ctx.sender_key,))
        ctx.reply("✅ Profil economy dihapus.")
    def profile(self,ctx,_):
        r=self._row(ctx); ctx.reply(f"🎒 *PROFILE*\nNama: {r['name']}\nLevel: {r['level']}\nEXP: {r['exp']}\nUang: Rp{r['money']:,}\nBank: Rp{r['bank']:,}")
    def _reward(self,ctx,money,exp,label):
        self._row(ctx)
        with self.store._lock,self.store._conn:self.store._conn.execute("UPDATE anya_users SET money=money+?,exp=exp+? WHERE user_jid=?",(money,exp,ctx.sender_key))
        ctx.reply(f"🧰 *{label}*\n+Rp{money:,}\n+{exp} EXP")
    def daily(self,ctx,_):
        r=self._row(ctx); now=int(time.time()); wait=24*3600-(now-r['daily_at'])
        if wait>0: raise ValueError(f"Harian sudah diambil. Coba lagi dalam {wait//3600}j {(wait%3600)//60}m.")
        reward=random.randint(1500,3500)
        with self.store._lock,self.store._conn:changed=self.store._conn.execute("UPDATE anya_users SET money=money+?,exp=exp+50,daily_at=? WHERE user_jid=? AND daily_at<=?",(reward,now,ctx.sender_key,now-86400)).rowcount
        if not changed:raise ValueError("Reward harian sudah diambil.")
        ctx.reply(f"🎁 Reward harian: *Rp{reward:,}* + 50 EXP")
    def work(self,ctx,_):
        r=self._row(ctx); now=int(time.time()); wait=600-(now-r['work_at'])
        if wait>0: raise ValueError(f"Istirahat dulu {wait//60}m {wait%60}s.")
        reward=random.randint(300,900)
        with self.store._lock,self.store._conn:changed=self.store._conn.execute("UPDATE anya_users SET money=money+?,exp=exp+20,work_at=? WHERE user_jid=? AND work_at<=?",(reward,now,ctx.sender_key,now-600)).rowcount
        if not changed:raise ValueError("Kerja masih cooldown.")
        ctx.reply(f"💼 Kerja selesai: +Rp{reward:,} +20 EXP")
    def activity(self,ctx,_): self._reward(ctx,random.randint(100,650),random.randint(5,25),"AKTIVITAS RPG")
    def deposit(self,ctx,args):
        r=self._row(ctx)
        try:
            if not re.fullmatch(r"[0-9][0-9., ]*",args.strip()):raise ValueError()
            n=int(re.sub(r"[., ]","",args))
        except:raise ValueError("Contoh: .deposit 500")
        if n<=0 or n>r['money']:raise ValueError("Saldo tunai tidak cukup.")
        with self.store._lock,self.store._conn:changed=self.store._conn.execute("UPDATE anya_users SET money=money-?,bank=bank+? WHERE user_jid=? AND money>=?",(n,n,ctx.sender_key,n)).rowcount
        if not changed:raise ValueError("Saldo tunai tidak cukup.")
        ctx.reply(f"🏦 Deposit Rp{n:,} berhasil.")
    def withdraw(self,ctx,args):
        r=self._row(ctx)
        try:
            if not re.fullmatch(r"[0-9][0-9., ]*",args.strip()):raise ValueError()
            n=int(re.sub(r"[., ]","",args))
        except:raise ValueError("Contoh: .withdraw 500")
        if n<=0 or n>r['bank']:raise ValueError("Saldo bank tidak cukup.")
        with self.store._lock,self.store._conn:changed=self.store._conn.execute("UPDATE anya_users SET bank=bank-?,money=money+? WHERE user_jid=? AND bank>=?",(n,n,ctx.sender_key,n)).rowcount
        if not changed:raise ValueError("Saldo bank tidak cukup.")
        ctx.reply(f"🏧 Withdraw Rp{n:,} berhasil.")
    def leaderboard(self,ctx,_):
        with self.store._lock: rows=self.store._conn.execute("SELECT name,level,exp,money+bank total FROM anya_users ORDER BY level DESC,exp DESC,total DESC LIMIT 10").fetchall()
        ctx.reply("🏆 *LEADERBOARD*\n"+"\n".join(f"{i+1}. {r['name']} — Lv.{r['level']} / {r['exp']} EXP" for i,r in enumerate(rows)))
    def levelup(self,ctx,_):
        r=self._row(ctx); need=r['level']*100
        if r['exp']<need:raise ValueError(f"Butuh {need} EXP. EXP kamu {r['exp']}.")
        with self.store._lock,self.store._conn:changed=self.store._conn.execute("UPDATE anya_users SET level=level+1,exp=exp-level*100 WHERE user_jid=? AND exp>=level*100",(ctx.sender_key,)).rowcount
        if not changed:raise ValueError("EXP belum cukup.")
        ctx.reply("⬆️ Level berhasil naik!")
    def limit(self,ctx,_): ctx.reply("♾️ Daffo-Botz Python tidak memakai limit command global. Gunakan fitur secara wajar.")


class AnyaDownloaderAliases:
    """Compatibility aliases mapped to Daffo's yt-dlp downloader."""
    VIDEO=("yt","ytdlp","tt","ttdl","tiktok","instagram","ig","facebook","fb","twitter","threads","videy","aio","aio2","douyin","bilibili")
    AUDIO=("ytmp3","yta","ttmp3","igmp3","igaudio")
    def __init__(self,router,downloader):
        for x in self.VIDEO: router.add(x,downloader.video)
        for x in self.AUDIO: router.add(x,downloader.audio)


class AnyaCompatibilityFeature:
    """Registers known Anya commands that need external/private APIs as discoverable placeholders.

    This prevents command collisions from silently disappearing while clearly telling
    the user which commands need a provider/API key or a future native port.
    """
    def __init__(self,router):
        self.router=router
        # Safe commands whose original implementation depends heavily on external APIs,
        # websites, credentials, JS-only rendering, or third-party services.
        names = {
          "bard","gemini","openai","jeeves","dolphin","felo","quillbot","airealtime","powerbrain","publicai","muslimai","kurumi","gita","epsilon","copilotth",
          "createimg","flux","aiimg","aivid","ghibli","jadikomik","nanobanana","editimage","editimg","hairstyle","upscale","imgprompt","imageprompt","gptprompt","toprompt",
          "animequotes","animerandom","otakudesu","bacakomik","komik","ongoing","animeinfo","bluearchive","storyanime",
          "gimg","lyrics","donghua","jadwalpuasa","cnbc","antara","komiku","komikindo",
          "pinterest","pinlive","pinvid","ttsearch","ttstalk","spotifysearch","webtoonsearch","playstoresearch","jobstreetsearch","applemusicsearch","stickersearch",
          "play","play2","ytplay","yts","spotifyplay",
          "removebg","removebg2","ssweb","tourl","tofile","whatmusic","songfinder","fotolive","hd","hdr","hdv","webp2mp4","togif","vn","tempo",
          "brat","brat2","brathd","bratvid","qc","iqc","iqc2","codesnap","ytcomment","faketweet","faketele","typogaleri2","tobotak","tochibi","tomanga",
          "showroom","cuaca","dashboard","dashboardlive","magma","notifberita",
        }
        for n in sorted(names):
            if not router.has(n): router.add(n,self.external)

    def external(self,ctx,args):
        cmd=ctx.text.lstrip(ctx.settings.prefix).split(maxsplit=1)[0]
        ctx.reply(
            f"🧩 *{cmd.upper()}* terdeteksi dari Daffo Feature Pack.\n\n"
            "Command ini sudah dicatat di compatibility layer, tetapi implementasi asli bergantung pada API/provider eksternal atau renderer JavaScript yang tidak aman untuk disalin mentah. "
            "Fitur inti Daffo-Botz tetap aktif; provider Python dapat ditambahkan lewat konfigurasi API."
        )
