from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from neonize.utils import build_jid

URL_RE = re.compile(r"(?i)\b(?:https?://|www\.)\S+|\b[a-z0-9.-]+\.(?:com|net|org|id|co|io|me|ly|app)(?:/\S*)?")
PHONE_RE = re.compile(r"\d{8,18}")


def jid_key(jid) -> str:
    return f"{getattr(jid, 'User', '')}@{getattr(jid, 'Server', '')}"


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if digits.startswith("0"):
        digits = "62" + digits[1:]
    return digits


def jid_from_string(value: str):
    value = value.strip().lstrip("@")
    if "@" in value:
        user, server = value.split("@", 1)
        return build_jid(user, server=server)
    phone = normalize_phone(value)
    if not PHONE_RE.fullmatch(phone):
        raise ValueError("Nomor/JID tidak valid")
    return build_jid(phone)


def _active_message_child(message):
    for name in (
        "extendedTextMessage",
        "imageMessage",
        "videoMessage",
        "documentMessage",
        "audioMessage",
        "stickerMessage",
    ):
        child = getattr(message, name, None)
        if child is not None:
            try:
                if child.ListFields():
                    return child
            except Exception:
                pass
    return None


def get_context_info(message):
    child = _active_message_child(message)
    if child is None:
        return None
    ctx = getattr(child, "contextInfo", None)
    if ctx is None:
        return None
    try:
        return ctx if ctx.ListFields() else None
    except Exception:
        return ctx


def media_message(event):
    for name in ("imageMessage", "videoMessage", "audioMessage", "stickerMessage", "documentMessage"):
        child = getattr(event.Message, name, None)
        try:
            if child is not None and child.ListFields():
                return event.Message
        except Exception:
            pass
    ctx = get_context_info(event.Message)
    if ctx is not None:
        quoted = getattr(ctx, "quotedMessage", None)
        try:
            if quoted is not None and quoted.ListFields():
                return quoted
        except Exception:
            pass
    return None


def target_jids_from_event(event, args: str) -> list:
    ctx = get_context_info(event.Message)
    values: list[str] = []
    if ctx is not None:
        values.extend(list(getattr(ctx, "mentionedJID", []) or []))
        participant = getattr(ctx, "participant", "")
        if participant:
            values.append(participant)
    if not values and args:
        values.extend(PHONE_RE.findall(args.replace("-", "")))
    seen = set()
    result = []
    for value in values:
        try:
            jid = jid_from_string(value)
        except ValueError:
            continue
        key = jid_key(jid)
        if key not in seen:
            result.append(jid)
            seen.add(key)
    return result


def contains_link(text: str) -> bool:
    return bool(URL_RE.search(text or ""))


def validate_public_http_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL harus diawali http:// atau https://")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("Host lokal tidak diizinkan")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
        raise ValueError("Alamat IP lokal/private tidak diizinkan")
