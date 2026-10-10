import asyncio
import time
from collections import OrderedDict

class TTLCache:
    def __init__(self, limit=10000): self.items=OrderedDict();self.limit=limit
    def claim(self, key, seconds):
        now=time.monotonic()
        if self.items.get(key,0)>now: return False
        self.items[key]=now+seconds;self.items.move_to_end(key)
        while len(self.items)>self.limit: self.items.popitem(last=False)
        return True

class SendGate:
    """Pace actual sends without letting one chat hold the global lock while sleeping."""
    def __init__(self, settings=None):
        self.lock=asyncio.Lock();self.last=0.;self.chats=OrderedDict();self.settings=settings
    async def wait(self, chat):
        while True:
            async with self.lock:
                cfg=self.settings() if self.settings else None
                global_gap=cfg.send_interval if cfg else .3
                chat_gap=cfg.chat_send_interval if cfg else .7
                now=time.monotonic()
                delay=max(self.last+global_gap-now,self.chats.get(chat,0)+chat_gap-now,0)
                if delay<=0:
                    self.last=now;self.chats[chat]=now;self.chats.move_to_end(chat)
                    while len(self.chats)>10000:self.chats.popitem(last=False)
                    return
            await asyncio.sleep(delay)
