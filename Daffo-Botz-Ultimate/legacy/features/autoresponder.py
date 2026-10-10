class AutoResponderFeature:
    RESPONSES = {
        "halo": "Halo juga! 👋 Ketik *.menu* untuk melihat fitur Daffo-Botz.",
        "hai": "Hai! 👋 Ada yang bisa dibantu? Ketik *.menu*.",
        "assalamualaikum": "Waalaikumsalam 👋 Semoga harimu menyenangkan.",
        "p": "Halo 👋 Jangan lupa tuliskan pesannya juga ya.",
    }

    def __init__(self, settings):
        self.settings = settings

    def process(self, ctx) -> bool:
        if not self.settings.auto_responder:
            return False
        response = self.RESPONSES.get(ctx.text.strip().lower())
        if response:
            ctx.reply(response.replace(".menu", f"{self.settings.prefix}menu"))
            return True
        return False
