from __future__ import annotations

import re

from neonize.utils.enum import ParticipantChange

from ..utils import contains_link


class ModerationFeature:
    DOWNLOAD_COMMANDS = {"dl", "mp3"}

    def __init__(self, router, settings, store, permissions):
        self.settings = settings
        self.store = store
        self.permissions = permissions
        router.add("antilink", self.cmd_antilink)
        router.add("antitoxic", self.cmd_antitoxic)

    def _toggle(self, ctx, args: str, flag: str, label: str) -> None:
        self.permissions.require_admin(ctx)
        state = args.strip().lower()
        if state not in {"on", "off"}:
            current = self.store.get_group_settings(ctx.chat_key)[flag]
            ctx.reply(f"{label}: *{'ON' if current else 'OFF'}* — gunakan `on` atau `off`.")
            return
        enabled = state == "on"
        self.store.set_group_flag(ctx.chat_key, flag, enabled)
        ctx.reply(f"🛡️ {label} sekarang *{'ON' if enabled else 'OFF'}*.")

    def cmd_antilink(self, ctx, args: str) -> None:
        self._toggle(ctx, args, "anti_link", "Anti-Link")

    def cmd_antitoxic(self, ctx, args: str) -> None:
        self._toggle(ctx, args, "anti_toxic", "Anti-Toxic")

    def _contains_toxic(self, text: str) -> bool:
        lowered = text.lower()
        for word in self.settings.toxic_words:
            if re.search(rf"(?<!\w){re.escape(word)}(?!\w)", lowered):
                return True
        return False

    def _is_downloader_command(self, text: str) -> bool:
        if not text.startswith(self.settings.prefix):
            return False
        cmd = text[len(self.settings.prefix):].split(maxsplit=1)[0].lower()
        return cmd in self.DOWNLOAD_COMMANDS

    def process(self, ctx) -> bool:
        if not ctx.is_group or not ctx.text:
            return False
        group_settings = self.store.get_group_settings(ctx.chat_key)
        if not group_settings["anti_link"] and not group_settings["anti_toxic"]:
            return False
        if self.permissions.is_group_admin(ctx):
            return False

        violation = None
        if (
            group_settings["anti_link"]
            and contains_link(ctx.text)
            and not self._is_downloader_command(ctx.text)
        ):
            violation = "link eksternal"
        elif group_settings["anti_toxic"] and self._contains_toxic(ctx.text):
            violation = "kata yang diblokir"

        if not violation:
            return False

        try:
            ctx.client.revoke_message(ctx.chat, ctx.sender, ctx.event.Info.ID)
        except Exception:
            pass

        strikes = self.store.add_strike(ctx.chat_key, ctx.sender_key)
        if strikes >= self.settings.strike_limit:
            try:
                ctx.client.update_group_participants(
                    ctx.chat,
                    [ctx.sender],
                    ParticipantChange.REMOVE,
                )
                ctx.reply(f"🚫 Pelanggaran berulang ({strikes}×). Anggota dikeluarkan.")
                self.store.reset_strike(ctx.chat_key, ctx.sender_key)
            except Exception:
                ctx.reply(
                    f"⚠️ Terdeteksi {violation}. Strike {strikes}/{self.settings.strike_limit}. "
                    "Bot tidak berhasil melakukan kick; pastikan bot adalah admin."
                )
        else:
            ctx.reply(
                f"⚠️ Pesan mengandung {violation}. Strike: *{strikes}/{self.settings.strike_limit}*."
            )
        return True
