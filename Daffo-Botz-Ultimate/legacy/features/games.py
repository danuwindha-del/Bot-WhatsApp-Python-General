from __future__ import annotations

import html
import json
import random
import threading
from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass
class GameSession:
    kind: str
    answer: str
    options: dict[str, str] | None = None


class GamesFeature:
    WORDS = [
        ("komputer", "Perangkat elektronik untuk mengolah data"),
        ("pelangi", "Fenomena warna di langit setelah hujan"),
        ("perpustakaan", "Tempat menyimpan dan membaca banyak buku"),
        ("oksigen", "Gas yang dibutuhkan manusia untuk bernapas"),
        ("demokrasi", "Sistem pemerintahan yang melibatkan suara rakyat"),
        ("algoritma", "Urutan langkah logis untuk menyelesaikan masalah"),
    ]

    def __init__(self, router):
        self._sessions: dict[str, GameSession] = {}
        self._lock = threading.RLock()
        router.add("tebakkata", self.tebak_kata)
        router.add("susunkata", self.susun_kata)
        router.add("trivia", self.trivia)
        router.add("jawab", self.answer)

    def _save(self, ctx, session: GameSession) -> None:
        with self._lock:
            getattr(self,"other_sessions",{}).pop(ctx.chat_key,None)
            if len(self._sessions)>=700:self._sessions.pop(next(iter(self._sessions)))
            self._sessions[ctx.chat_key] = session

    def tebak_kata(self, ctx, _args: str) -> None:
        word, clue = random.choice(self.WORDS)
        self._save(ctx, GameSession("tebakkata", word))
        ctx.reply(
            f"🧠 *TEBAK KATA*\n"
            f"Petunjuk: _{clue}_\n"
            "Jawab dengan `.jawab <kata>`"
        )

    def susun_kata(self, ctx, _args: str) -> None:
        word, clue = random.choice(self.WORDS)
        letters = list(word)
        scrambled = word
        while scrambled == word:
            random.shuffle(letters)
            scrambled = "".join(letters)
        self._save(ctx, GameSession("susunkata", word))
        ctx.reply(
            f"🔤 *SUSUN KATA*\n"
            f"Huruf: `{scrambled.upper()}`\n"
            f"Petunjuk: _{clue}_\n"
            "Jawab dengan `.jawab <kata>`"
        )

    def trivia(self, ctx, _args: str) -> None:
        try:
            req = Request(
                "https://opentdb.com/api.php?amount=1&type=multiple",
                headers={"User-Agent": "Daffo-Botz/1.0"},
            )
            with urlopen(req, timeout=8) as response:
                payload = json.loads(response.read().decode("utf-8"))
            item = payload["results"][0]
            question = html.unescape(item["question"])
            correct = html.unescape(item["correct_answer"])
            choices = [correct] + [html.unescape(x) for x in item["incorrect_answers"]]
            random.shuffle(choices)
            options = {chr(65 + i): choice for i, choice in enumerate(choices)}
            self._save(ctx, GameSession("trivia", correct, options))
            lines = "\n".join(f"{k}. {v}" for k, v in options.items())
            ctx.reply(
                f"🎓 *TRIVIA*\n{question}\n\n{lines}\n\n"
                "Jawab: `.jawab A` atau `.jawab <teks>`"
            )
        except Exception:
            ctx.reply("⚠️ Server trivia sedang tidak tersedia. Coba lagi nanti.")

    def answer(self, ctx, args: str) -> None:
        if not args:
            raise ValueError("Masukkan jawaban.")
        with self._lock:
            session = self._sessions.get(ctx.chat_key)
        if session is None:
            raise ValueError(
                "Tidak ada game aktif. Mulai dengan .tebakkata, .susunkata, atau .trivia"
            )
        candidate = args.strip()
        if session.options and candidate.upper() in session.options:
            candidate = session.options[candidate.upper()]
        if candidate.casefold() == session.answer.casefold():
            with self._lock:
                self._sessions.pop(ctx.chat_key, None)
            ctx.reply(f"✅ *BENAR!* Jawabannya: *{session.answer}* 🎉")
        else:
            ctx.reply("❌ Belum tepat. Coba lagi!")
