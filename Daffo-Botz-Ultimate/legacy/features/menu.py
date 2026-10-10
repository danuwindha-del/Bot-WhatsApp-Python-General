class MenuFeature:
    def __init__(self, router, settings):
        self.settings = settings
        self.router = router
        router.add("menu", self.menu, aliases=("help", "allmenu"))

    def menu(self, ctx, _args: str) -> None:
        p = self.settings.prefix
        menu = f"""
╭━━━〔 *{self.settings.bot_name.upper()}* 〕━━━╮
┃ 🤖 _Python + Neonize WhatsApp Bot_
┃ Prefix: `{p}`
┃ Anya v7 Compatibility Pack: ✅
╰━━━━━━━━━━━━━━━━━━━━╯

*👥 GROUP*
• `{p}hidetag [pesan]` — semua anggota boleh pakai
• `{p}tagall [pesan]` — tag terlihat
• `{p}open` / `{p}close`
• `{p}add 628xxx` / `{p}kick @user`
• `{p}promote @user` / `{p}demote @user`
• `{p}setname` / `{p}setdesc` / `{p}setpp`
• `{p}adminlist` / `{p}kickme`
• `{p}linkgc` / `{p}revoke`
• `{p}welcome on|off`

*🛡️ MODERATION*
• `{p}antilink on|off`
• `{p}antitoxic on|off`

*📥 DOWNLOADER*
• `{p}dl <url>` / `{p}mp3 <url>`
• aliases video: `{p}yt`, `{p}ytdlp`, `{p}tt`, `{p}tiktok`, `{p}instagram`, `{p}facebook`, `{p}twitter`, `{p}threads`
• aliases audio: `{p}ytmp3`, `{p}yta`, `{p}ttmp3`, `{p}igmp3`

*🎨 MEDIA & TOOLS*
• `{p}sticker` / `{p}s`
• `{p}qrcode <teks>` / `{p}barcode <teks>`
• `{p}calc <rumus>`
• `{p}resize 512x512` / `{p}blur [radius]`
• `{p}compress` / `{p}toimg` / `{p}tomp3`
• `{p}translate en|teks`
• `{p}wiki <kata>` / `{p}kbbi <kata>` / `{p}doa <kata>`

*🎮 GAMES ANYA + DAFFO*
• `{p}tebakkata` / `{p}susunkata`
• `{p}tebakbenda` / `{p}tebakbuah`
• `{p}tebakgambar` / `{p}tebaklogo`
• `{p}tebaklagu` / `{p}tebaklirik`
• `{p}tebakkimia` / `{p}tebaktebakan`
• `{p}siapakahaku` / `{p}family100`
• `{p}tebakwarna` / `{p}hangman`
• `{p}trivia` / `{p}dadu` / `{p}slot`
• `{p}jawab <jawaban>` / `{p}nyerah`

*🎭 FUN*
• `{p}truth` / `{p}dare`
• `{p}pilih a|b` / `{p}angka [max]`
• `{p}cekiq` / `{p}cekcantik` / `{p}gantengcek`
• `{p}ceksifat` / `{p}cekkhodam` / `{p}stress`
• `{p}quotebucin` / `{p}sadboy` / `{p}carabalikan`

*💰 ECONOMY / RPG*
• `{p}daftar <nama>` / `{p}profile`
• `{p}harian` / `{p}kerja` / `{p}claim`
• `{p}mining` / `{p}mancing` / `{p}berburu`
• `{p}nguli` / `{p}mulung` / `{p}nebang`
• `{p}deposit <jumlah>` / `{p}withdraw <jumlah>`
• `{p}leaderboard` / `{p}levelup`

*ℹ️ INFO*
• `{p}ping` / `{p}runtime` / `{p}statusbot`
• `{p}botinfo` / `{p}totalfitur`
• `{p}owner` / `{p}creator`

*
_Total command terdaftar saat bot hidup: {self.router.command_count}_
""".strip()
        ctx.reply(menu)
