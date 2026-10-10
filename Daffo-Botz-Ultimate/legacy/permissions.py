from __future__ import annotations

from .utils import jid_key


class PermissionService:
    def __init__(self, settings):
        self.settings = settings

    def is_owner(self, ctx) -> bool:
        return getattr(ctx.sender,"Server","")=="s.whatsapp.net" and ctx.sender_number in self.settings.owner_numbers

    def is_group_admin(self, ctx) -> bool:
        if self.is_owner(ctx):
            return True
        if not ctx.is_group:
            return False
        info = ctx.client.get_group_info(ctx.chat)
        sender = ctx.sender_key
        for participant in getattr(info, "Participants", []) or []:
            candidates = [
                getattr(participant, "JID", None),
                getattr(participant, "LID", None),
                getattr(participant, "PhoneNumber", None),
            ]
            if sender in {jid_key(j) for j in candidates if j is not None}:
                return bool(
                    getattr(participant, "IsAdmin", False)
                    or getattr(participant, "IsSuperAdmin", False)
                )
        return False

    def require_group(self, ctx) -> None:
        if not ctx.is_group:
            raise PermissionError("Perintah ini hanya dapat dipakai di grup.")

    def require_admin(self, ctx) -> None:
        self.require_group(ctx)
        if not self.is_group_admin(ctx):
            raise PermissionError("Perintah ini hanya untuk admin grup.")
