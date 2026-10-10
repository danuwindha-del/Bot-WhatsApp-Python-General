from __future__ import annotations

import threading

from ..utils import jid_key


class WelcomeFeature:
    def __init__(self, router, store, permissions, settings):
        self.store = store
        self.permissions = permissions
        self.settings = settings
        self._cache: dict[str, set[str]] = {}
        self._lock = threading.RLock()
        router.add("welcome", self.cmd_welcome)

    def cmd_welcome(self, ctx, args: str) -> None:
        self.permissions.require_admin(ctx)
        state = args.strip().lower()
        if state not in {"on", "off"}:
            current = self.store.get_group_settings(ctx.chat_key)["welcome"]
            ctx.reply(f"Welcome message: *{'ON' if current else 'OFF'}* — gunakan `on` atau `off`.")
            return
        enabled = state == "on"
        self.store.set_group_flag(ctx.chat_key, "welcome", enabled)
        ctx.reply(f"👋 Welcome message sekarang *{'ON' if enabled else 'OFF'}*.")

    def seed(self, client) -> None:
        try:
            groups = client.get_joined_groups()
        except Exception:
            return
        for group in groups or []:
            try:
                info = client.get_group_info(group.JID)
                members = {
                    jid_key(p.JID)
                    for p in getattr(info, "Participants", []) or []
                    if getattr(p, "JID", None) is not None
                }
                with self._lock:
                    self._cache[jid_key(info.JID)] = members
            except Exception:
                continue

    def _find_group_jid(self, event):
        for name in ("JID", "GroupJID", "Chat"):
            value = getattr(event, name, None)
            if value is not None and getattr(value, "Server", "") == "g.us":
                return value
        for parent_name in ("Info", "GroupInfo", "MessageSource"):
            parent = getattr(event, parent_name, None)
            if parent is None:
                continue
            for name in ("JID", "Chat", "GroupJID"):
                value = getattr(parent, name, None)
                if value is not None and getattr(value, "Server", "") == "g.us":
                    return value
        return None

    def on_group_update(self, client, event) -> None:
        group_jid = self._find_group_jid(event)
        if group_jid is None:
            return
        key = jid_key(group_jid)
        try:
            info = client.get_group_info(group_jid)
        except Exception:
            return
        participants = list(getattr(info, "Participants", []) or [])
        current = {jid_key(p.JID) for p in participants if getattr(p, "JID", None) is not None}
        with self._lock:
            before = self._cache.get(key)
            self._cache[key] = current
        if before is None:
            return
        joined = current - before
        if not joined or not self.store.get_group_settings(key)["welcome"]:
            return
        group_name_obj = getattr(info, "GroupName", None)
        group_name = (
            getattr(info, "Name", "")
            or getattr(group_name_obj, "Name", "")
            or "grup ini"
        )
        by_key = {jid_key(p.JID): p.JID for p in participants if getattr(p, "JID", None) is not None}
        for member_key in joined:
            member = by_key.get(member_key)
            if member is None:
                continue
            mention = f"@{member.User}"
            text = (
                f"╭━━〔 *WELCOME* 〕━━╮\n"
                f"✨ Selamat datang {mention}!\n"
                f"📍 *{group_name}*\n\n"
                f"Semoga betah, saling menghargai, dan jangan lupa baca aturan grup. 🌟\n"
                f"╰━━━ *{self.settings.bot_name}* ━━━╯"
            )
            client.send_message(
                group_jid,
                text,
                ghost_mentions=mention,
                mentions_are_lids=getattr(member, "Server", "") == "lid",
            )
