from ..utils import media_message


class StickerFeature:
    def __init__(self, router, settings):
        self.settings = settings
        router.add("sticker", self.make_sticker, aliases=("s",))

    def make_sticker(self, ctx, _args: str) -> None:
        msg = media_message(ctx.event)
        if msg is None:
            raise ValueError("Kirim/reply gambar, GIF, atau video pendek lalu jalankan .sticker")
        data = ctx.client.download_any(msg)
        if not data:
            raise ValueError("Media tidak dapat diunduh.")
        ctx.client.send_sticker(
            ctx.chat,
            data,
            name=self.settings.bot_name,
            packname=f"{self.settings.bot_name} Stickers",
        )
