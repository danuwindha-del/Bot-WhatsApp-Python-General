import random
from collections import OrderedDict
from bot.limits import TTLCache


games = OrderedDict()


async def ping(ctx, args):
    await ctx.reply('🟢 *DAFFO-BOTZ ONLINE*\nRuntime async aktif dan siap melayani.')


async def ai(ctx, args):
    # Kept for compatibility; normal messages already go directly to Daffo AI.
    await ctx.bot.send(ctx.chat, await ctx.bot.ask_ai(ctx, args or 'Halo Daffo BOT'))


async def reset(ctx, args):
    ctx.bot.ai.clear(ctx.memory_key)
    await ctx.reply('🧠 Memori percakapan Daffo AI untuk chat ini sudah dibersihkan.')


async def dl(ctx, args):
    await ctx.bot.downloader.handle(ctx, args)


async def vn(ctx, args):
    await ctx.bot.downloader.handle(ctx, args, True)


async def dice(ctx, args):
    if not ctx.bot.store.config.entertainment:
        raise ValueError('Hiburan sedang dinonaktifkan oleh admin.')
    await ctx.reply(f'🎲 Daffo melempar dadu: *{random.randint(1, 6)}*')


async def quiz(ctx, args):
    if not ctx.bot.store.config.entertainment:
        raise ValueError('Hiburan sedang dinonaktifkan oleh admin.')
    question, answer = random.choice([
        ('Ibu kota Indonesia yang dikenal dengan Monas?', 'jakarta'),
        ('Planet merah?', 'mars'),
        ('Hewan penghasil madu?', 'lebah'),
    ])
    games[ctx.chat_key] = answer
    while len(games) > 500:
        games.popitem(last=False)
    await ctx.reply('🧠 *DAFFO QUIZ*\n' + question + '\nJawab: `.jawab jawaban` • Menyerah: `.nyerah`')


async def answer(ctx, args):
    expected = games.get(ctx.chat_key)
    if not expected:
        raise ValueError('Belum ada permainan aktif. Ketik .tebakkata')
    if args.strip().casefold() == expected:
        games.pop(ctx.chat_key)
        await ctx.reply('✅ Benar! Daffo kasih nilai 100 buat kamu 😎')
    else:
        await ctx.reply('❌ Belum tepat. Coba lagi, Daffo masih nunggu jawabanmu.')


async def surrender(ctx, args):
    await ctx.reply('🏳️ Jawabannya: *' + games.pop(ctx.chat_key, 'Belum ada permainan.') + '*')


async def _toggle(ctx, key, args, label):
    await ctx.group_admin()
    value = args.strip().lower()
    if value not in ('on', 'off'):
        command = key.replace('_', '')
        raise ValueError(f'Gunakan .{command} on atau .{command} off')
    enabled = value == 'on'
    await ctx.bot.store.update({key: enabled})
    await ctx.reply(f'🛡️ {label}: *{"ON" if enabled else "OFF"}*')


async def antilink(ctx, args):
    await _toggle(ctx, 'anti_link', args, 'Anti-link')


async def antitoxic(ctx, args):
    await _toggle(ctx, 'anti_toxic', args, 'Anti-toxic')


async def welcome(ctx, args):
    await _toggle(ctx, 'welcome', args, 'Welcome message')


def register(router):
    router.update(
        ping=ping, statusbot=ping,
        ai=ai, resetai=reset,
        dl=dl, vn=vn, mp3=vn, tt=dl, tiktok=dl, yt=dl, instagram=dl,
        dadu=dice, tebakkata=quiz, jawab=answer, nyerah=surrender,
        antilink=antilink, antitoxic=antitoxic, welcome=welcome,
    )
