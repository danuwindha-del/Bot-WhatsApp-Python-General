from __future__ import annotations

from collections.abc import Callable


class CommandRouter:
    def __init__(self, prefix: str):
        self.prefix = prefix
        self._handlers: dict[str, Callable] = {}

    def add(self, name: str, handler: Callable, aliases: tuple[str, ...] = ()) -> None:
        self._handlers[name.lower()] = handler
        for alias in aliases:
            self._handlers[alias.lower()] = handler

    def has(self, name: str) -> bool:
        return name.lower() in self._handlers

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    @property
    def command_count(self) -> int:
        return len(self._handlers)

    def dispatch(self, ctx) -> bool:
        text = ctx.text
        if not text.startswith(self.prefix):
            return False
        body = text[len(self.prefix):].strip()
        if not body:
            return False
        command, _, args = body.partition(" ")
        handler = self._handlers.get(command.lower())
        if handler is None:
            return False
        try:
            handler(ctx, args.strip())
        except PermissionError as exc:
            ctx.reply(f"⛔ {exc}")
        except ValueError as exc:
            ctx.reply(f"⚠️ {exc}")
        except Exception as exc:
            ctx.reply(f"❌ Gagal menjalankan perintah: {exc}")
        return True
