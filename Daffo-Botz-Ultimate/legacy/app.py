from __future__ import annotations

import logging

from neonize.client import NewClient
from neonize.events import ConnectedEv, GroupInfoEv, MessageEv

from .config import Settings
from .context import ChatContext
from .permissions import PermissionService
from .router import CommandRouter
from .storage import SQLiteStore
from .features.autoresponder import AutoResponderFeature
from .features.downloader import DownloaderFeature
from .features.games import GamesFeature
from .features.group import GroupFeature
from .features.menu import MenuFeature
from .features.moderation import ModerationFeature
from .features.sticker import StickerFeature
from .features.welcome import WelcomeFeature
from .features.anya_pack import (
    AnyaCompatibilityFeature, AnyaDownloaderAliases, AnyaEconomyFeature,
    AnyaFunFeature, AnyaGameFeature, AnyaGroupExtrasFeature, AnyaInfoFeature,
    AnyaInternetFeature, AnyaToolsFeature,
)


class DaffoBot:
    def __init__(self) -> None:
        self.settings = Settings.load()
        self.store = SQLiteStore(self.settings.app_db, self.settings.welcome_default)
        self.client = NewClient(str(self.settings.session_db))
        self.router = CommandRouter(self.settings.prefix)
        self.permissions = PermissionService(self.settings)

        MenuFeature(self.router, self.settings)
        GroupFeature(self.router, self.permissions)
        self.moderation = ModerationFeature(
            self.router, self.settings, self.store, self.permissions
        )
        self.autoresponder = AutoResponderFeature(self.settings)
        self.welcome = WelcomeFeature(
            self.router, self.store, self.permissions, self.settings
        )
        StickerFeature(self.router, self.settings)
        downloader = DownloaderFeature(self.router, self.settings)
        GamesFeature(self.router)

        # Anya v7 -> Python integration pack. Existing Daffo commands are kept;
        # new aliases/features are layered on top without removing the old modules.
        self.started_at = __import__("time").time()
        AnyaGameFeature(self.router)
        AnyaFunFeature(self.router)
        AnyaGroupExtrasFeature(self.router, self.permissions)
        AnyaInternetFeature(self.router)
        AnyaToolsFeature(self.router)
        AnyaEconomyFeature(self.router, self.store)
        AnyaDownloaderAliases(self.router, downloader)
        AnyaInfoFeature(self.router, self.settings, self.started_at)
        AnyaCompatibilityFeature(self.router)

        self.client.event(ConnectedEv)(self._on_connected)
        self.client.event(MessageEv)(self._on_message)
        self.client.event(GroupInfoEv)(self._on_group_info)

    def _on_connected(self, client: NewClient, _event: ConnectedEv) -> None:
        logging.info("%s connected to WhatsApp", self.settings.bot_name)
        self.welcome.seed(client)

    def _on_group_info(self, client: NewClient, event: GroupInfoEv) -> None:
        try:
            self.welcome.on_group_update(client, event)
        except Exception:
            logging.exception("Failed to process group update")

    def _on_message(self, client: NewClient, event: MessageEv) -> None:
        try:
            source = event.Info.MessageSource
            if bool(getattr(source, "IsFromMe", False)):
                return
            if getattr(source.Chat, "Server", "") == "broadcast":
                return
            ctx = ChatContext(client, event, self.settings, self.store)
            if not ctx.text:
                return
            if self.moderation.process(ctx):
                return
            if self.router.dispatch(ctx):
                return
            self.autoresponder.process(ctx)
        except Exception:
            logging.exception("Message handler failed")

    def run(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
        logging.info("Starting %s", self.settings.bot_name)
        self.client.connect()
