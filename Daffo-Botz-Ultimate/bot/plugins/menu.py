from neonize.ext.interactive_message.button import ButtonMessage


CATEGORIES = {
    'utama': [
        ('Daffo AI', 'Chat biasa langsung dibalas AI', '.menu ai'),
        ('Group Control', 'Hide tag, add/kick, admin, setpp', '.menu grup'),
        ('Media', 'Downloader, sticker, converter', '.menu media'),
        ('Games', 'Quiz, tebak-tebakan, game dataset', '.menu games'),
        ('Fun', 'Truth/dare dan fitur santai', '.menu fun'),
        ('Economy', 'RPG, kerja, daily, leaderboard', '.menu economy'),
        ('Tools', 'QR, kalkulator, resize, blur', '.menu tools'),
        ('Internet', 'Wiki, KBBI, translate, doa', '.menu internet'),
        ('Info', 'Status, runtime, owner', '.menu info'),
    ],
    'ai': [
        ('Chat bebas', 'Cukup kirim pesan biasa, tanpa .ai', 'Halo Daffo'),
        ('Reset memori', 'Hapus konteks AI chat ini', '.resetai'),
        ('AI manual', 'Kompatibilitas command lama', '.ai pertanyaan'),
    ],
    'grup': [
        ('Hide tag', 'Semua anggota boleh pakai', '.hidetag pesan'),
        ('Tambah anggota', 'Admin: nomor internasional', '.add 628xxxx'),
        ('Kick', 'Admin: mention/reply/nomor', '.kick @user'),
        ('Promote', 'Jadikan admin', '.promote @user'),
        ('Demote', 'Turunkan admin', '.demote @user'),
        ('Buka grup', 'Izinkan semua mengirim', '.open'),
        ('Tutup grup', 'Hanya admin mengirim', '.close'),
        ('Set nama', 'Ubah nama grup', '.setname nama'),
        ('Set deskripsi', 'Ubah deskripsi grup', '.setdesc teks'),
        ('Set foto', 'Reply foto lalu jalankan', '.setpp'),
        ('Tag all', 'Tag seluruh anggota', '.tagall pesan'),
        ('Admin list', 'Daftar admin grup', '.adminlist'),
        ('Link grup', 'Ambil invite link', '.linkgc'),
    ],
    'media': [
        ('Video', 'YouTube/TikTok/Instagram', '.dl URL'),
        ('Voice note', 'Ambil audio/voice', '.vn URL'),
        ('Sticker', 'Reply gambar/video', '.sticker'),
        ('To MP3', 'Reply media', '.tomp3'),
        ('To image', 'Konversi sticker/media', '.toimg'),
        ('Compress', 'Kompresi media', '.compress'),
    ],
    'games': [
        ('Tebak kata', 'Quiz kata', '.tebakkata'),
        ('Susun kata', 'Susun huruf', '.susunkata'),
        ('Tebak gambar', 'Game gambar', '.tebakgambar'),
        ('Tebak buah', 'Game buah', '.tebakbuah'),
        ('Tebak logo', 'Game logo', '.tebaklogo'),
        ('Family 100', 'Game Family100', '.family100'),
        ('Hangman', 'Game hangman', '.hangman'),
        ('Menyerah', 'Lihat jawaban', '.nyerah'),
    ],
    'fun': [
        ('Truth', 'Pertanyaan truth acak', '.truth'),
        ('Dare', 'Tantangan acak', '.dare'),
        ('Pilih', 'Daffo pilihkan opsi', '.pilih nasi | mie'),
        ('Cek IQ', 'Skor hiburan', '.cekiq'),
        ('Cek sifat', 'Sifat versi game', '.ceksifat'),
        ('Cek khodam', 'Hiburan random', '.cekkhodam'),
        ('Quote bucin', 'Quote santai', '.quotebucin'),
    ],
    'economy': [
        ('Daftar', 'Buat profil economy', '.daftar nama'),
        ('Profile', 'Lihat profil', '.profile'),
        ('Harian', 'Claim daily', '.harian'),
        ('Kerja', 'Cari uang dan EXP', '.kerja'),
        ('Mining', 'Aktivitas RPG', '.mining'),
        ('Deposit', 'Simpan uang', '.deposit 500'),
        ('Withdraw', 'Ambil uang', '.withdraw 500'),
        ('Leaderboard', 'Peringkat pengguna', '.leaderboard'),
    ],
    'tools': [
        ('QR Code', 'Buat QR dari teks/link', '.qrcode teks'),
        ('Kalkulator', 'Hitung ekspresi', '.calc (12+8)*3'),
        ('Resize', 'Resize gambar', '.resize'),
        ('Blur', 'Blur gambar', '.blur'),
    ],
    'internet': [
        ('Wikipedia', 'Ringkasan Wikipedia', '.wiki Indonesia'),
        ('KBBI', 'Kamus lokal', '.kbbi algoritma'),
        ('Translate', 'Terjemahkan teks', '.translate en|selamat pagi'),
        ('Doa', 'Doa pilihan', '.doa makan'),
    ],
    'info': [
        ('Ping', 'Status cepat bot', '.ping'),
        ('Runtime', 'Lama bot berjalan', '.runtime'),
        ('Bot info', 'Informasi Daffo-Botz', '.botinfo'),
        ('Owner', 'Informasi pembuat', '.owner'),
        ('All menu', 'Daftar semua command', '.allmenu'),
    ],
}


def _header():
    return (
        '╭━━━〔 🤖 *DAFFO-BOTZ* 〕━━━╮\n'
        '┃  Smart WhatsApp Assistant\n'
        '┃  AI • Group • Media • Games • Tools\n'
        '╰━━━━━━━━━━━━━━━━━━━━╯'
    )


async def menu(ctx, args):
    category = args.strip().lower() or 'utama'
    entries = CATEGORIES.get(category, CATEGORIES['utama'])
    body = 'Pilih fitur Daffo-Botz. AI tersedia jika diaktifkan dan API key sudah diisi.'
    button = ButtonMessage().set_title('DAFFO-BOTZ • SMART HUB').set_body(body).set_footer('Made by Lord Daffo • 085648175452')
    button.add_reply('Menu utama', '.menu').add_reply('Status', '.ping')
    button.add_selection('Jelajahi fitur').add_section('Daffo Services')
    for title, desc, command in entries:
        button.add_row(title, desc, command)
    if not ctx.bot.store.config.interactive:
        return await plain(ctx, category)
    await ctx.bot.gate.wait(ctx.chat_key)
    try:
        await ctx.bot.client.send_interactive_message(ctx.chat, button)
        ctx.bot.outgoing += 1
    except Exception:
        ctx.bot.log('Menu interaktif gagal; memakai menu teks.')
        await plain(ctx, category)


async def plain(ctx, args):
    category = args.strip().lower() or 'utama'
    entries = CATEGORIES.get(category, CATEGORIES['utama'])
    lines = [_header(), '', f'✨ *Kategori: {category.upper()}*']
    for title, desc, cmd in entries:
        lines.append(f'• *{title}* — `{cmd}`\n  _{desc}_')
    lines += ['', '💬 *Daffo AI:* kirim pesan biasa jika AI diaktifkan admin.', '📚 Ketik `.allmenu` untuk daftar semua command.']
    await ctx.reply('\n'.join(lines))


async def allmenu(ctx, args):
    commands = sorted(ctx.bot.router)
    chunks = []
    current = []
    size = 0
    for name in commands:
        item = '.' + name
        if size + len(item) + 3 > 3200:
            chunks.append(current); current=[]; size=0
        current.append(item); size += len(item)+3
    if current: chunks.append(current)
    for i, chunk in enumerate(chunks, 1):
        title = f'🤖 *DAFFO-BOTZ • ALL COMMANDS* ({i}/{len(chunks)})\n'
        await ctx.bot.send(ctx.chat, title + ' • '.join(chunk))


def register(router):
    router['menu'] = menu
    router['help'] = menu
    router['menuteks'] = plain
    router['allmenu'] = allmenu
