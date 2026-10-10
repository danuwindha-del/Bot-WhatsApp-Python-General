from dataclasses import dataclass
import json
from neonize.utils.message import extract_text


def jid(value):
    return f'{value.User}@{value.Server}'


def text_of(message):
    for _ in range(3):
        if message.HasField('ephemeralMessage'):
            message = message.ephemeralMessage.message
        else:
            break
    for field, attr in [('buttonsResponseMessage', 'selectedButtonID'), ('templateButtonReplyMessage', 'selectedID')]:
        if message.HasField(field):
            return getattr(getattr(message, field), attr)
    if message.HasField('listResponseMessage'):
        return message.listResponseMessage.singleSelectReply.selectedRowID
    if message.HasField('interactiveResponseMessage'):
        try:
            data = json.loads(message.interactiveResponseMessage.nativeFlowResponseMessage.paramsJSON)
            return str(data.get('id', '')) if isinstance(data, dict) else ''
        except (ValueError, TypeError):
            return ''
    return (extract_text(message) or '').strip()


@dataclass
class Context:
    bot: object
    event: object
    text: str
    command_name: str = ''
    command_args: str = ''

    @property
    def chat(self):
        return self.event.Info.MessageSource.Chat

    @property
    def sender(self):
        return self.event.Info.MessageSource.Sender

    @property
    def chat_key(self):
        return jid(self.chat)

    @property
    def sender_key(self):
        return jid(self.sender)

    @property
    def sender_number(self):
        return getattr(self.sender, 'User', '')

    @property
    def is_group(self):
        return self.chat.Server == 'g.us'

    @property
    def memory_key(self):
        return (self.chat_key, jid(self.sender))

    async def reply(self, text):
        await self.bot.smart_reply(self, str(text)[:6000])

    async def group_admin(self):
        if not self.is_group:
            raise ValueError('Perintah ini hanya untuk grup.')
        info = await self.bot.client.get_group_info(self.chat)
        for p in info.Participants:
            identities = [jid(p.JID)]
            for attr in ('PhoneNumber', 'LID'):
                value = getattr(p, attr, None)
                if value is not None and hasattr(value, 'User'):
                    identities.append(jid(value))
            if jid(self.sender) in identities and (p.IsAdmin or p.IsSuperAdmin):
                return info
        if self.sender.Server == 's.whatsapp.net' and self.sender.User in self.bot.store.config.admins:
            return info
        raise ValueError('Perintah ini hanya untuk admin grup atau admin bot terdaftar.')
