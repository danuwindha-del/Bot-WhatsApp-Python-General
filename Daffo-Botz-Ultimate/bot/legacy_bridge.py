import asyncio
import inspect
from concurrent.futures import ThreadPoolExecutor
import time
from pathlib import Path

from legacy.permissions import PermissionService
from legacy.storage import SQLiteStore
from legacy.features.group import GroupFeature
from legacy.features.sticker import StickerFeature
from legacy.features.games import GamesFeature
from legacy.features.anya_pack import (
    AnyaCompatibilityFeature,
    AnyaEconomyFeature,
    AnyaFunFeature,
    AnyaGameFeature,
    AnyaGroupExtrasFeature,
    AnyaInfoFeature,
    AnyaInternetFeature,
    AnyaToolsFeature,
)


class LegacySettingsAdapter:
    def __init__(self, bot):
        self.bot = bot

    @property
    def bot_name(self):
        return 'Daffo-Botz'

    @property
    def prefix(self):
        return '.'

    @property
    def owner_numbers(self):
        return frozenset(self.bot.store.config.admins)

    @property
    def session_db(self):
        return self.bot.store.directory / 'whatsapp-session.db'

    @property
    def app_db(self):
        return self.bot.store.directory / 'legacy.db'

    @property
    def max_download_mb(self):
        return self.bot.store.config.max_download_mb

    @property
    def welcome_default(self):
        return self.bot.store.config.welcome

    @property
    def auto_responder(self):
        return False

    @property
    def strike_limit(self):
        return self.bot.store.config.strike_limit

    @property
    def toxic_words(self):
        return tuple(self.bot.store.config.toxic_words)


class SyncClientProxy:
    """Makes the async Neonize client callable from legacy sync handlers running in a worker thread."""

    def __init__(self, bot, loop, context):
        self.bot = bot
        self.loop = loop
        self.context = context

    def _run(self, awaitable, timeout=35):
        future = asyncio.run_coroutine_threadsafe(awaitable, self.loop)
        try:return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise ValueError("Fitur melewati batas waktu.") from None

    def __getattr__(self, name):
        target = getattr(self.bot.client, name)
        if not callable(target):
            return target

        def call(*args, **kwargs):
            async def invoke():
                if not self.context.active or not self.bot.running: raise ValueError('Permintaan dibatalkan.')
                sending=name.startswith(('send_', 'reply_'))
                if sending: await self.bot.gate.wait(self.context.chat_key)
                if not self.context.active or not self.bot.running: raise ValueError('Permintaan dibatalkan.')
                result=target(*args,**kwargs)
                if inspect.isawaitable(result): result=await result
                if sending:self.bot.outgoing+=1
                if name=='update_group_participants' and result:
                    failures=[p for p in result if getattr(p,'Error',0)]
                    if failures: raise ValueError('WhatsApp menolak perubahan peserta (kode '+','.join(str(p.Error) for p in failures)+'). Periksa izin/privacy atau gunakan undangan grup.')
                return result
            return self._run(invoke(),timeout=35)
        return call


class LegacyContextBridge:
    def __init__(self, modern, settings, legacy_store, loop):
        self.modern = modern
        self.bot = modern.bot
        self.event = modern.event
        self.settings = settings
        self.store = legacy_store
        self.active = True
        self.client = SyncClientProxy(self.bot, loop, self)

    @property
    def text(self):
        return self.modern.text

    @property
    def chat(self):
        return self.modern.chat

    @property
    def sender(self):
        return self.modern.sender

    @property
    def chat_key(self):
        return self.modern.chat_key

    @property
    def sender_key(self):
        return self.modern.sender_key

    @property
    def sender_number(self):
        return self.modern.sender_number

    @property
    def is_group(self):
        return self.modern.is_group

    def _run(self, awaitable, timeout=35):
        async def checked():
            if not self.active or not self.bot.running:
                if inspect.iscoroutine(awaitable):awaitable.close()
                raise ValueError('Permintaan dibatalkan.')
            return await awaitable
        future = asyncio.run_coroutine_threadsafe(checked(), self.bot.loop)
        try:return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise ValueError("Fitur melewati batas waktu.") from None

    def reply(self, text):
        return self._run(self.modern.reply(str(text)[:6000]))

    def send(self, text, **kwargs):
        return self.reply(text)


class LegacyRouterAdapter:
    def __init__(self, bot, settings, legacy_store):
        self.bot = bot
        self.settings = settings
        self.legacy_store = legacy_store

    def has(self, name):
        return name.lower() in self.bot.router

    @property
    def commands(self):
        return tuple(sorted(self.bot.router))

    @property
    def command_count(self):
        return len(self.bot.router)

    def add(self, name, handler, aliases=()):
        for command in (name, *aliases):
            command = command.lower()

            async def wrapped(ctx, args, _handler=handler):
                legacy_ctx = LegacyContextBridge(ctx, self.settings, self.legacy_store, self.bot.loop)
                try:
                    pack=self.bot.legacy
                    if pack.slots.locked():raise ValueError('Fitur berat sedang penuh. Coba lagi sebentar.')
                    await pack.slots.acquire()
                    future=self.bot.loop.run_in_executor(pack.executor,_handler,legacy_ctx,args)
                    def done(f):
                        pack.slots.release()
                        if not f.cancelled():f.exception()
                    future.add_done_callback(done)
                    await asyncio.shield(future)
                except PermissionError as exc:
                    raise ValueError(str(exc)) from None
                finally:
                    legacy_ctx.active=False

            self.bot.router[command] = wrapped
            cls=type(getattr(handler,'__self__',None)).__name__
            category='games' if 'Game' in cls else 'fun' if 'Fun' in cls else 'economy' if 'Economy' in cls else 'group' if 'Group' in cls else 'tools'
            self.bot.command_meta[command]={'category':category,'status':'native','legacy':True}


class LegacyPack:
    """Activates the safe Python features from the earlier Daffo/Anya pack inside the async runtime."""

    VIDEO_ALIASES = ('yt','ytdlp','tt','ttdl','tiktok','instagram','ig','facebook','fb','twitter','threads','videy','aio','aio2','douyin','bilibili')
    AUDIO_ALIASES = ('ytmp3','yta','ttmp3','igmp3','igaudio')

    def __init__(self, bot):
        self.bot = bot
        self.executor=ThreadPoolExecutor(max_workers=4,thread_name_prefix="daffo-feature")
        self.slots=asyncio.Semaphore(4)
        self.settings = LegacySettingsAdapter(bot)
        self.store = SQLiteStore(bot.store.directory / 'legacy.db', bot.store.config.welcome)
        self.router = LegacyRouterAdapter(bot, self.settings, self.store)
        permissions = PermissionService(self.settings)

        GroupFeature(self.router, permissions)
        StickerFeature(self.router, self.settings)
        games=GamesFeature(self.router)
        anya=AnyaGameFeature(self.router)
        games.other_sessions=anya.sessions
        anya.other_sessions=games._sessions
        def answer(ctx,args):
            if ctx.chat_key in anya.sessions: return anya.answer(ctx,args)
            return games.answer(ctx,args)
        def surrender(ctx,args):
            if ctx.chat_key in anya.sessions:return anya.give_up(ctx,args)
            session=games._sessions.pop(ctx.chat_key,None)
            if not session:raise ValueError('Tidak ada permainan aktif.')
            ctx.reply('🏳️ Jawabannya: '+session.answer)
        self.router.add('jawab',answer)
        self.router.add('nyerah',surrender)
        for name in ('jawab','nyerah'):bot.command_meta[name]['category']='games' 
        AnyaFunFeature(self.router)
        AnyaGroupExtrasFeature(self.router, permissions)
        AnyaInternetFeature(self.router)
        AnyaToolsFeature(self.router)
        AnyaEconomyFeature(self.router, self.store)
        AnyaInfoFeature(self.router, self.settings, time.time())

        # External-provider commands are retained, but their fallback is replaced
        # below with Daffo AI instead of the old migration/compatibility message.
        before = set(bot.router)
        AnyaCompatibilityFeature(self.router)
        generated = set(bot.router) - before
        for name in generated:
            bot.router[name] = self._ai_external(name)
            bot.command_meta[name]['status']='provider'

        # AI aliases use the configured model; they do not pretend to switch providers.
        async def ai_alias(ctx,args):
            if not args:raise ValueError('Tambahkan pertanyaan setelah command AI.')
            await ctx.reply(await bot.ask_ai(ctx,args))
        for name in ('bard','gemini','openai','jeeves','dolphin','felo','quillbot','airealtime','powerbrain','publicai','muslimai','kurumi','gita','epsilon','copilotth'):
            bot.router[name]=ai_alias
            bot.command_meta[name]={'category':'ai','status':'native','legacy':True}

        # Downloader aliases use the newer async downloader, not the old blocking implementation.
        for name in self.VIDEO_ALIASES:
            bot.router[name] = bot.router['dl']
        for name in self.AUDIO_ALIASES:
            bot.router[name] = bot.router['vn']

    async def close(self):
        await asyncio.to_thread(self.executor.shutdown, wait=True, cancel_futures=True)
        self.store.close()

    def _ai_external(self, name):
        async def handler(ctx, args):
            await ctx.reply(f'🤖 Fitur .{name} belum memiliki provider native. Belum ada file atau tindakan yang dihasilkan. Ketik kebutuhanmu dalam chat biasa agar Daffo AI membantu, atau pilih fitur berstatus native di dashboard.')
        return handler
