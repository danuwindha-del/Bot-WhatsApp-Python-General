import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit
import aiosqlite
from cryptography.fernet import Fernet
from pydantic import BaseModel, Field, ConfigDict, field_validator


class Config(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

    anti_link: bool = False
    anti_toxic: bool = False
    entertainment: bool = True
    ai_vision: bool = True
    ai_vision_model: str = Field(default="", max_length=100)
    ai_knowledge: bool = True
    ai: bool = True
    ai_private: bool = True
    ai_group: bool = True
    ai_command_assist: bool = True
    downloader: bool = True
    welcome: bool = True
    interactive: bool = True
    legacy_features: bool = True

    welcome_message: str = Field(
        default='✨ Selamat datang {user} di *{group}*!\nSemoga betah bersama keluarga Daffo-Botz 🤖',
        max_length=1000,
    )
    admins: list[str] = Field(default_factory=list, max_length=50)
    toxic_words: list[str] = Field(default_factory=list, max_length=100)

    ai_base_url: str = 'https://bandelbanget.xyz/v1'
    ai_model: str = Field(default='auto', min_length=1, max_length=100)
    ai_key: str = Field(default='', max_length=500)
    ai_temperature: float = Field(default=0.55, ge=0.0, le=1.5)
    ai_max_tokens: int = Field(default=1000, ge=128, le=3000)
    ai_memory_turns: int = Field(default=12, ge=2, le=30)
    ai_system_prompt: str = Field(
        default=(
            'Kamu adalah Daffo BOT, asisten WhatsApp utama Daffo-Botz. '
            'Kamu dibuat oleh Lord Daffo. Nomor pembuat/owner: 085648175452. '
            'Jika ditanya siapa kamu, jelaskan dengan jelas: "Saya adalah Daffo BOT yang dibuat oleh Lord Daffo, 085648175452." '
            'Gunakan bahasa pengguna, ramah, cerdas, santai tetapi tetap sopan. '
            'Bantu pengguna memahami fitur bot, perintah, informasi umum, ide, belajar, dan percakapan sehari-hari. '
            'Jangan mengaku sudah menjalankan tindakan yang sebenarnya belum dilakukan. '
            'Jangan mengarang status sistem, hasil unduhan, atau hasil moderasi. '
            'Untuk jawaban WhatsApp, utamakan format ringkas, mudah dibaca, dan tidak terlalu kaku.'
        ),
        max_length=5000,
    )

    send_interval: float = Field(default=0.3, ge=0.1, le=5.0)
    chat_send_interval: float = Field(default=0.7, ge=0.2, le=10.0)
    ai_tools: bool = True
    ai_timeout: int = Field(default=25, ge=5, le=90)
    ai_group_mode: str = 'all'
    ai_history_chars: int = Field(default=16000, ge=2000, le=50000)
    cooldown: int = Field(default=0, ge=0, le=60)

    @field_validator('ai_group_mode')
    @classmethod
    def group_mode(cls, value):
        if value not in ('all', 'mention'): raise ValueError('Mode grup harus all/mention')
        return value

    max_download_mb: int = Field(default=90, ge=10, le=250)
    strike_limit: int = Field(default=3, ge=1, le=10)

    @field_validator('admins')
    @classmethod
    def numbers(cls, values):
        if any(not x.isdigit() or not 8 <= len(x) <= 15 for x in values):
            raise ValueError('Nomor admin harus angka internasional, contoh 6281234567890')
        return values

    @field_validator('ai_base_url')
    @classmethod
    def endpoint(cls, value):
        u = urlsplit(value)
        allowed = [x.strip() for x in os.getenv('AI_ALLOWED_HOSTS', 'bandelbanget.xyz').split(',') if x.strip()]
        if u.scheme != 'https' or u.hostname not in allowed or u.username or u.password or u.query or u.fragment or u.port not in (None, 443):
            raise ValueError('Gunakan HTTPS dan host dalam AI_ALLOWED_HOSTS')
        return value.rstrip('/')


class Store:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.config = Config()
        self.lock = asyncio.Lock()
        self.cipher = Fernet(os.environ['ENCRYPTION_KEY'].encode())

    async def open(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        self.db = await aiosqlite.connect(self.directory / 'control.db')
        await self.db.execute('PRAGMA journal_mode=WAL')
        await self.db.execute('CREATE TABLE IF NOT EXISTS config(id INTEGER PRIMARY KEY, payload TEXT)')
        row = await (await self.db.execute('SELECT payload FROM config WHERE id=1')).fetchone()
        if row:
            data = json.loads(row[0])
            if data.get('ai_key'):
                data['ai_key'] = self.cipher.decrypt(data['ai_key'].encode()).decode()
            self.config = Config(**data)
        from bot.training import Training
        self.training = Training(self)
        await self.training.open()
        os.chmod(self.directory / 'control.db', 0o600)

    async def update(self, patch):
        async with self.lock:
            data = self.config.model_dump()
            data.update(patch)
            new = Config(**data)
            saved = new.model_dump()
            if saved['ai_key']:
                saved['ai_key'] = self.cipher.encrypt(saved['ai_key'].encode()).decode()
            await self.db.execute('INSERT OR REPLACE INTO config VALUES(1,?)', (json.dumps(saved),))
            await self.db.commit()
            self.config = new
        return self.public()

    def public(self):
        result = self.config.model_dump()
        result['ai_key_configured'] = bool(result.pop('ai_key'))
        return result

    async def close(self):
        await self.db.close()
