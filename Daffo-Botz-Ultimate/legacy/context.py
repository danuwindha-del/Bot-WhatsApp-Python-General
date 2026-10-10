from __future__ import annotations

from dataclasses import dataclass

from neonize.utils.message import extract_text

from .utils import jid_key


@dataclass
class ChatContext:
    client: object
    event: object
    settings: object
    store: object

    @property
    def text(self) -> str:
        try:
            return (extract_text(self.event.Message) or "").strip()
        except Exception:
            return ""

    @property
    def chat(self):
        return self.event.Info.MessageSource.Chat

    @property
    def sender(self):
        return self.event.Info.MessageSource.Sender

    @property
    def chat_key(self) -> str:
        return jid_key(self.chat)

    @property
    def sender_key(self) -> str:
        return jid_key(self.sender)

    @property
    def sender_number(self) -> str:
        return getattr(self.sender, "User", "")

    @property
    def is_group(self) -> bool:
        return getattr(self.chat, "Server", "") == "g.us"

    def reply(self, text: str) -> None:
        self.client.reply_message(text, self.event)

    def send(self, text: str, **kwargs) -> None:
        self.client.send_message(self.chat, text, **kwargs)
