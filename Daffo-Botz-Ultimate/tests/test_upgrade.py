import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx
import pytest
from neonize.proto.Neonize_pb2 import JID,Message as Event
from bot.calculator import calculate
from bot.config import Store
from bot.runtime import Bot
from bot.assistant_tools import Toolbox
from bot.ai import DaffoAI
from bot.wiki import Wikipedia
from bot.scheduler import Scheduler
from test_system import env,client,login

@pytest.mark.parametrize('expression,answer',[
 ('12+8','20'),('12-8','4'),('12 × 8','96'),('12x8','96'),('12 / 8','1.5'),('12 ÷ 3','4'),
 ('(12+8)*3/2','30'),('2^8','256'),('15% * 200000','30000'),('sqrt(81)','9'),
 ('10 kali 5 kurang 8','42'),('2,5 * 4','10'),('abs(-7)','7'),('10 // 3','3'),('sin(pi/2)','1')])
def test_calculator_operations(expression,answer):assert calculate(expression)==answer

@pytest.mark.parametrize('expression',['__import__("os").system("id")','"a"*10000000','2**1000000000','9**9**9','1/0','(1).__class__','sqrt(-1)','[1,2]','True+1'])
def test_calculator_bounds(expression):
    with pytest.raises(ValueError):calculate(expression)

@pytest.mark.asyncio
async def test_wiki_search_schema_cache_and_source():
    requests=[]
    def handler(req):
        requests.append(req);assert req.url.params['generator']=='search'
        return httpx.Response(200,json={'query':{'pages':[{'title':'Fotosintesis','extract':'Proses mengubah energi cahaya.'}]}})
    wiki=Wikipedia(httpx.MockTransport(handler))
    try:
        result=await wiki.search('fotosintesis');assert result['url']=='https://id.wikipedia.org/wiki/Fotosintesis'
        assert await wiki.search('FOTOSINTESIS')==result and len(requests)==1
    finally:await wiki.close()

@pytest.mark.asyncio
async def test_wiki_error_is_readable():
    wiki=Wikipedia(httpx.MockTransport(lambda r:httpx.Response(503)))
    try:
        with pytest.raises(ValueError,match='belum dapat'):await wiki.search('x')
    finally:await wiki.close()

@pytest.mark.asyncio
async def test_fair_scheduler():
    q=Scheduler(3);q.put_nowait('a1','a');q.put_nowait('a2','a');q.put_nowait('b1','b')
    with pytest.raises(asyncio.QueueFull):q.put_nowait('overflow','c')
    assert await q.fast.get()==('a','a1')
    assert await q.fast.get()==('b','b1')
    q.fast.done('a');assert await q.fast.get()==('a','a2');q.fast.done('a');q.fast.done('b')
    assert q.qsize()==0 and not q.fast.pending

@pytest.mark.asyncio
async def test_tools_real_results_and_no_privileged_execution(env):
    store=Store(env);await store.open();bot=Bot(store,'demo');await bot.start()
    try:
        tool=Toolbox(bot)
        r=await tool.execute({'function':{'name':'calculate','arguments':'{"expression":"12*8"}'}})
        assert r=={'ok':True,'text':'96'}
        bot.router['kick']=AsyncMock()
        r=await tool.execute({'function':{'name':'bot_command','arguments':'{"command":"kick","args":"62812345678"}'}})
        assert not r['ok'] and 'Belum dijalankan' in r['text'];bot.router['kick'].assert_not_awaited()
    finally:await bot.close();await store.close()

@pytest.mark.asyncio
async def test_ai_native_tools_roundtrip(env):
    store=Store(env);await store.open();await store.update({'ai_key':'fake'})
    bot=Bot(store,'demo');await bot.start();calls=[]
    def respond(req):
        data=json.loads(req.content);calls.append(data)
        if len(calls)==1:return httpx.Response(200,json={'choices':[{'message':{'role':'assistant','content':None,'tool_calls':[{'id':'c1','type':'function','function':{'name':'calculate','arguments':'{"expression":"12*8"}'}}]}}]})
        assert json.loads(data['messages'][-1]['content'])['text']=='96'
        return httpx.Response(200,json={'choices':[{'message':{'content':'Hasilnya 96.'}}]})
    ai=DaffoAI(store,httpx.MockTransport(respond))
    try:
        assert await ai.ask('user','Hitung 12 kali 8',toolbox=Toolbox(bot))=='Hasilnya 96.'
        assert ai.tool_calls==1 and len(calls)==2
    finally:await ai.close();await bot.close();await store.close()

@pytest.mark.asyncio
async def test_provider_without_tools_falls_back(env):
    store=Store(env);await store.open();await store.update({'ai_key':'fake'})
    def handler(req):
        if 'tools' in json.loads(req.content):return httpx.Response(400,json={'error':'unsupported tools'})
        return httpx.Response(200,json={'choices':[{'message':{'content':'Halo!'}}]})
    ai=DaffoAI(store,httpx.MockTransport(handler))
    try:
        assert await ai.ask('u','halo',toolbox=SimpleNamespace(schemas=Toolbox.schemas))=='Halo!'
        assert ai.tools_supported is False
    finally:await ai.close();await store.close()

@pytest.mark.asyncio
async def test_command_context_and_no_polish_request(env):
    store=Store(env);await store.open();bot=Bot(store,'demo');await bot.start();bot.send=AsyncMock()
    try:
        bot.ai.enhance_command=AsyncMock(side_effect=AssertionError('must not call AI'))
        ctx=SimpleNamespace(command_name='calc',memory_key=('chat','sender'),chat='chat')
        await bot.smart_reply(ctx,'96')
        bot.send.assert_awaited_once_with('chat','96');bot.ai.enhance_command.assert_not_awaited()
        assert bot.ai.context[ctx.memory_key][-1][2]=='96'
    finally:await bot.close();await store.close()

class Capture:
    def __init__(self,bot):
        self.bot=bot;self.chat_key='test@g.us';self.sender_key='123@s.whatsapp.net';self.sender_number='123'
        self.chat=JID(User='test',Server='g.us');self.sender=JID(User='123',Server='s.whatsapp.net')
        self.memory_key=(self.chat_key,self.sender_key);self.is_group=True
        self.text='';self.event=None;self.outputs=[];self.command_name='';self.command_args=''
    async def reply(self,text):self.outputs.append(text)

@pytest.mark.asyncio
async def test_games_kbbi_switches_and_live_legacy_toggle(env):
    store=Store(env);await store.open();await store.update({'legacy_features':False})
    bot=Bot(store,'demo');await bot.start();ctx=Capture(bot)
    try:
        with pytest.raises(ValueError):await bot.execute_command(ctx,'tebakkata','')
        await store.update({'legacy_features':True})
        await bot.execute_command(ctx,'tebakkata','')
        await bot.execute_command(ctx,'nyerah','');assert 'Jawabannya' in ctx.outputs[-1]
        await bot.execute_command(ctx,'susunkata','');await bot.execute_command(ctx,'nyerah','')
        await bot.execute_command(ctx,'tebakbendera','');assert 'Negara' in ctx.outputs[-1]
        await bot.execute_command(ctx,'kbbi','a');assert 'tidak memuat definisi' in ctx.outputs[-1]
        await store.update({'entertainment':False})
        for command in ('tebakkata','dadu','truth','nyerah'):
            with pytest.raises(ValueError,match='Hiburan'):await bot.execute_command(ctx,command,'')
    finally:await bot.close();await store.close()

@pytest.mark.asyncio
async def test_group_description_and_revoke_api_signature(env):
    store=Store(env);await store.open();bot=Bot(store,'demo');await bot.start();ctx=Capture(bot)
    participant=SimpleNamespace(JID=ctx.sender,LID=None,PhoneNumber=None,IsAdmin=True,IsSuperAdmin=False)
    bot.client=SimpleNamespace(get_group_info=AsyncMock(return_value=SimpleNamespace(Participants=[participant],GroupTopic=SimpleNamespace(TopicID='old'))),
                               set_group_topic=AsyncMock(),get_group_invite_link=AsyncMock(return_value='https://chat.whatsapp.com/test'))
    try:
        await bot.execute_command(ctx,'setdesc','deskripsi baru')
        args=bot.client.set_group_topic.call_args.args
        assert len(args)==4 and args[1]=='old' and args[3]=='deskripsi baru'
        await bot.execute_command(ctx,'revoke','')
        bot.client.get_group_invite_link.assert_awaited_once_with(ctx.chat,revoke=True)
    finally:await bot.close();await store.close()

@pytest.mark.asyncio
async def test_fast_command_not_blocked_by_ai(env):
    store=Store(env);await store.open();bot=Bot(store,'demo');await bot.start()
    hold=asyncio.Event();fast=asyncio.Event();busy=0;started=asyncio.Event()
    async def handle(ev):
        nonlocal busy
        if ev.Message.conversation.startswith('.'):
            fast.set();return
        busy+=1
        if busy==4:started.set()
        await hold.wait()
    bot.handle=handle
    def event(i,text):
        e=Event();e.Info.ID=str(i);e.Info.MessageSource.Chat.CopyFrom(JID(User=str(i),Server='s.whatsapp.net'));e.Info.MessageSource.Sender.CopyFrom(JID(User=str(i),Server='s.whatsapp.net'));e.Message.conversation=text;return e
    try:
        for i in range(4):await bot.receive(None,event(i,'hello'))
        await asyncio.wait_for(started.wait(),1)
        await bot.receive(None,event(9,'.ping'))
        await asyncio.wait_for(fast.wait(),.5)
        assert not hold.is_set()
    finally:hold.set();await bot.close();await store.close()

def test_dashboard_diagnostics_export_auth(client):
    for path in ('diagnostics','config/export','commands'):assert client.get('/api/'+path).status_code==401
    h=login(client)
    assert client.patch('/api/config',json={'ai_key':'do-not-export','ai_timeout':15,'ai_group_mode':'mention','cooldown':0},headers=h).status_code==200
    r=client.get('/api/config/export');assert r.status_code==200 and 'do-not-export' not in r.text and 'ai_key' not in r.json()
    assert client.get('/api/diagnostics').json()['version']=='3.2'
    catalog=client.get('/api/commands').json()['catalog']
    assert any(x['name']=='calc' and x['status']=='native' for x in catalog)
    assert any(x['name']=='flux' and x['status']=='provider' for x in catalog)
    assert client.post('/api/ai/test',json={'prompt':'hello'}).status_code==403

def test_docker_contains_legacy():assert 'legacy' not in Path('.dockerignore').read_text().splitlines()

@pytest.mark.asyncio
async def test_clear_ai_during_inflight_does_not_restore_memory(env):
    store=Store(env);await store.open();await store.update({'ai_key':'test'})
    started=asyncio.Event();release=asyncio.Event()
    async def handler(req):
        started.set();await release.wait()
        return httpx.Response(200,json={'choices':[{'message':{'content':'ok'}}]})
    ai=DaffoAI(store,httpx.MockTransport(handler))
    try:
        task=asyncio.create_task(ai.ask('k','hello'));await started.wait();ai.clear('k');release.set()
        assert await task=='ok' and 'k' not in ai.history
    finally:await ai.close();await store.close()

@pytest.mark.asyncio
async def test_ai_bot_command_uses_legacy_reply_capture(env):
    store=Store(env);await store.open();bot=Bot(store,'demo');await bot.start()
    try:
        r=await Toolbox(bot,Capture(bot)).execute({'function':{'name':'bot_command','arguments':'{"command":"kbbi","args":"a"}'}})
        assert r['ok'] and 'daftar kata lokal' in r['text']
    finally:await bot.close();await store.close()

@pytest.mark.asyncio
async def test_economy_rejects_negative_amount_and_preserves_balance(env):
    store=Store(env);await store.open();bot=Bot(store,'demo');await bot.start();ctx=Capture(bot)
    try:
        await bot.execute_command(ctx,'daftar','Tester')
        with pytest.raises(ValueError):await bot.execute_command(ctx,'deposit','-100')
        await bot.execute_command(ctx,'deposit','500');await bot.execute_command(ctx,'withdraw','200')
        r=bot.legacy.store._conn.execute('SELECT money,bank FROM anya_users WHERE user_jid=?',(ctx.sender_key,)).fetchone()
        assert r['money']==700 and r['bank']==300
    finally:await bot.close();await store.close()

@pytest.mark.asyncio
async def test_moderation_applies_strike_limit(env):
    store=Store(env);await store.open();await store.update({'anti_link':True,'strike_limit':2})
    bot=Bot(store,'demo');await bot.start();bot.send=AsyncMock()
    bot.client=SimpleNamespace(get_group_info=AsyncMock(return_value=SimpleNamespace(Participants=[])),revoke_message=AsyncMock(),update_group_participants=AsyncMock(return_value=[]))
    e=Event();e.Info.ID='1';e.Info.MessageSource.Chat.CopyFrom(JID(User='123',Server='g.us'));e.Info.MessageSource.Sender.CopyFrom(JID(User='456',Server='s.whatsapp.net'));e.Message.conversation='https://example.com'
    try:
        await bot.handle(e);assert bot.client.update_group_participants.await_count==0
        await bot.handle(e);assert bot.client.update_group_participants.await_count==1
        assert bot.legacy.store._conn.execute('SELECT count(*) FROM strikes').fetchone()[0]==0
    finally:await bot.close();await store.close()
