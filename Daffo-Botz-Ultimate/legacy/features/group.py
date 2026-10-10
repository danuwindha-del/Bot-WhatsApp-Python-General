from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps
from neonize.utils.enum import ParticipantChange

from ..utils import get_context_info, target_jids_from_event


class GroupFeature:
    def __init__(self, router, permissions):
        self.permissions = permissions
        router.add("hidetag", self.hidetag, aliases=("htag",))
        router.add("open", self.open_group)
        router.add("close", self.close_group)
        router.add("add", self.add)
        router.add("kick", self.kick, aliases=("remove",))
        router.add("promote", self.promote)
        router.add("demote", self.demote)
        router.add("setname", self.set_name)
        router.add("setdesc", self.set_desc)
        router.add("setpp", self.set_photo)

    def hidetag(self, ctx, args: str) -> None:
        """Hide-tag seluruh peserta. Boleh dipakai semua anggota grup."""
        self.permissions.require_group(ctx)
        info = ctx.client.get_group_info(ctx.chat)
        participant_jids = []
        for participant in getattr(info, "Participants", []) or []:
            jid = getattr(participant, "JID", None)
            if jid is not None and getattr(jid, "User", ""):
                participant_jids.append(jid)

        if not participant_jids:
            raise ValueError("Daftar anggota grup tidak tersedia.")

        use_lids = all(
            getattr(jid, "Server", "") == "lid" for jid in participant_jids
        )
        ghost_mentions = " ".join(f"@{jid.User}" for jid in participant_jids)
        message = args.strip() or "📢 *Perhatian untuk seluruh anggota grup.*"

        ctx.client.send_message(
            ctx.chat,
            message,
            ghost_mentions=ghost_mentions,
            mentions_are_lids=use_lids,
        )

    def open_group(self, ctx, _args: str) -> None:
        self.permissions.require_admin(ctx)
        ctx.client.set_group_announce(ctx.chat, False)
        ctx.reply("🔓 *GRUP DIBUKA*\n\nSemua anggota sekarang dapat mengirim pesan.")

    def close_group(self, ctx, _args: str) -> None:
        self.permissions.require_admin(ctx)
        ctx.client.set_group_announce(ctx.chat, True)
        ctx.reply("🔒 *GRUP DITUTUP*\n\nHanya admin yang dapat mengirim pesan.")

    def _targets(self, ctx, args: str):
        targets = target_jids_from_event(ctx.event, args)
        if not targets:
            raise ValueError(
                "Target tidak ditemukan.\n\n"
                "Gunakan tag, reply pesan target, atau nomor WhatsApp.\n"
                "Contoh: `.kick @user` atau `.add 6281234567890`"
            )
        return targets

    def add(self, ctx, args: str) -> None:
        self.permissions.require_admin(ctx)
        targets = self._targets(ctx, args)

        try:
            ctx.client.update_group_participants(
                ctx.chat,
                targets,
                ParticipantChange.ADD,
            )
            ctx.reply("✅ *ADD MEMBER*\n\nPermintaan menambahkan anggota berhasil dikirim.")
        except Exception as exc:
            error = str(exc).lower()

            if "463" in error or "account_reachout_restricted" in error:
                try:
                    invite = ctx.client.get_group_invite_link(ctx.chat)
                    ctx.reply(
                        "⚠️ *TIDAK BISA MENAMBAHKAN LANGSUNG*\n\n"
                        "WhatsApp membatasi penambahan langsung untuk akun/nomor ini.\n\n"
                        "Gunakan link undangan grup berikut:\n"
                        f"{invite}\n\n"
                        "Nomor tersebut dapat bergabung melalui link secara manual."
                    )
                except Exception:
                    ctx.reply(
                        "⚠️ *ADD DIBATASI WHATSAPP*\n\n"
                        "Server WhatsApp menolak penambahan langsung "
                        "(463: account_reachout_restricted).\n\n"
                        "Coba gunakan link undangan grup atau tambahkan secara manual. "
                        "Jangan mengulang `.add` berkali-kali."
                    )
                return

            if "403" in error:
                ctx.reply(
                    "⚠️ *PRIVASI PENGGUNA*\n\n"
                    "Nomor tidak dapat ditambahkan langsung. Kemungkinan pengaturan "
                    "privasi pengguna mengharuskan undangan grup."
                )
                return

            if "404" in error:
                ctx.reply(
                    "❌ *NOMOR TIDAK DITEMUKAN*\n\n"
                    "Pastikan nomor terdaftar di WhatsApp dan gunakan format 62xxxxxxxxxxx."
                )
                return

            raise

    def kick(self, ctx, args: str) -> None:
        self.permissions.require_admin(ctx)
        ctx.client.update_group_participants(
            ctx.chat,
            self._targets(ctx, args),
            ParticipantChange.REMOVE,
        )
        ctx.reply("✅ *KICK MEMBER*\n\nAnggota berhasil dikeluarkan dari grup.")

    def promote(self, ctx, args: str) -> None:
        self.permissions.require_admin(ctx)
        ctx.client.update_group_participants(
            ctx.chat,
            self._targets(ctx, args),
            ParticipantChange.PROMOTE,
        )
        ctx.reply("✅ Anggota berhasil dipromosikan menjadi admin.")

    def demote(self, ctx, args: str) -> None:
        self.permissions.require_admin(ctx)
        ctx.client.update_group_participants(
            ctx.chat,
            self._targets(ctx, args),
            ParticipantChange.DEMOTE,
        )
        ctx.reply("✅ Admin berhasil diturunkan menjadi anggota.")

    def set_name(self, ctx, args: str) -> None:
        self.permissions.require_admin(ctx)
        if not args.strip():
            raise ValueError("Masukkan nama grup baru. Contoh: `.setname Daffo Community`")
        ctx.client.set_group_name(ctx.chat, args.strip()[:100])
        ctx.reply("✅ Nama grup berhasil diperbarui.")

    def set_desc(self, ctx, args: str) -> None:
        self.permissions.require_admin(ctx)
        if not args.strip():
            raise ValueError("Masukkan deskripsi grup baru. Contoh: `.setdesc Grup resmi Daffo-Botz`")
        import uuid
        info=ctx.client.get_group_info(ctx.chat)
        ctx.client.set_group_topic(ctx.chat, info.GroupTopic.TopicID, uuid.uuid4().hex, args.strip()[:2000])
        ctx.reply("✅ Deskripsi grup berhasil diperbarui.")

    @staticmethod
    def _get_image_message(event):
        message = event.Message

        image = getattr(message, "imageMessage", None)
        try:
            if image is not None and image.ListFields():
                return message
        except Exception:
            pass

        context = get_context_info(message)
        if context is not None:
            quoted = getattr(context, "quotedMessage", None)
            if quoted is not None:
                image = getattr(quoted, "imageMessage", None)
                try:
                    if image is not None and image.ListFields():
                        return quoted
                except Exception:
                    pass

                document = getattr(quoted, "documentMessage", None)
                try:
                    if document is not None and document.ListFields():
                        mimetype = (getattr(document, "mimetype", "") or "").lower()
                        if mimetype.startswith("image/"):
                            return quoted
                except Exception:
                    pass

        return None

    @staticmethod
    def _prepare_group_photo(data: bytes) -> bytes:
        if not data:
            raise ValueError("Data gambar kosong.")

        try:
            with Image.open(BytesIO(data)) as image:
                image = ImageOps.exif_transpose(image)
                try:
                    image.seek(0)
                except Exception:
                    pass

                if image.mode in ("RGBA", "LA"):
                    background = Image.new("RGB", image.size, "white")
                    alpha = image.getchannel("A")
                    background.paste(image, mask=alpha)
                    image = background
                elif image.mode == "P":
                    image = image.convert("RGBA")
                    background = Image.new("RGB", image.size, "white")
                    background.paste(image, mask=image.getchannel("A"))
                    image = background
                else:
                    image = image.convert("RGB")

                image = ImageOps.fit(
                    image,
                    (640, 640),
                    method=Image.Resampling.LANCZOS,
                    centering=(0.5, 0.5),
                )

                output = BytesIO()
                image.save(output, format="JPEG", quality=90, optimize=True)
                result = output.getvalue()
                if not result.startswith(b"\xff\xd8"):
                    raise ValueError("Konversi JPEG gagal.")
                return result
        except Exception as exc:
            raise ValueError(f"Gambar tidak valid atau tidak dapat diproses: {exc}") from exc

    def set_photo(self, ctx, _args: str) -> None:
        self.permissions.require_admin(ctx)
        message = self._get_image_message(ctx.event)
        if message is None:
            raise ValueError(
                "Gambar tidak ditemukan.\n\n"
                "Kirim foto dengan caption `.setpp`, atau reply sebuah foto lalu ketik `.setpp`."
            )

        data = ctx.client.download_any(message)
        if not data:
            raise ValueError("Gambar gagal diunduh dari WhatsApp.")

        photo = self._prepare_group_photo(data)
        ctx.client.set_group_photo(ctx.chat, photo)
        ctx.reply("✅ *GROUP PHOTO UPDATED*\n\nFoto profil grup berhasil diperbarui.")
