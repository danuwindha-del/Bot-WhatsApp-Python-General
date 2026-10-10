"""Fair, bounded per-conversation queues. A busy chat occupies at most one worker per lane."""
import asyncio
from collections import deque

class Lane:
    def __init__(self, owner):
        self.owner=owner;self.pending={};self.active=set();self.ready=asyncio.Queue()
    async def get(self):
        key=await self.ready.get()
        self.active.add(key)
        event=self.pending[key].popleft()
        self.owner.pending_count-=1
        return key,event
    def done(self,key):
        self.active.discard(key)
        if self.pending.get(key):self.ready.put_nowait(key)
        else:self.pending.pop(key,None)
        self.ready.task_done()
    def put(self,key,event):
        if key not in self.pending:
            self.pending[key]=deque()
            self.ready.put_nowait(key)
        self.pending[key].append(event)
    def clear(self):
        self.pending.clear();self.active.clear()
        while not self.ready.empty():self.ready.get_nowait();self.ready.task_done()

class Scheduler:
    def __init__(self,maxsize=250):
        self.maxsize=maxsize;self.pending_count=0;self.fast=Lane(self);self.slow=Lane(self)
    def put_nowait(self,event,key,slow=False):
        if self.pending_count>=self.maxsize:raise asyncio.QueueFull
        self.pending_count+=1
        (self.slow if slow else self.fast).put(key,event)
    def qsize(self):return self.pending_count
    def clear(self):
        self.fast.clear();self.slow.clear();self.pending_count=0
