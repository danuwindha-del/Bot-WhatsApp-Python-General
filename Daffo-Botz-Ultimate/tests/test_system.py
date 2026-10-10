import asyncio,json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import httpx,pytest
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from neonize.proto.Neonize_pb2 import JID,Message as Event
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message
from bot.config import Store,Config
from bot.ai import DattioAI
from bot.context import text_of
from bot.limits import TTLCache
from bot.media import validate_url,process
from bot.runtime import Bot
from bot.plugins.menu import menu
from web.app import create_app

@pytest.fixture
def env(tmp_path,monkeypatch):
    for k,v in {'ENCRYPTION_KEY':Fernet.generate_key().decode(),'ADMIN_PASSWORD_HASH':PasswordHasher().hash('Correct-password-123'),'ADMIN_USERNAME':'admin','PUBLIC_ORIGIN':'http://testserver','COOKIE_SECURE':'false','BOT_MODE':'demo','DATA_DIR':str(tmp_path)}.items():monkeypatch.setenv(k,v)
    return tmp_path
@pytest.fixture
def client(env):
    with TestClient(create_app()) as c:yield c

def login(c):
    r=c.post('/api/login',json={'username':'admin','password':'Correct-password-123'},headers={'Origin':'http://testserver'})
    assert r.status_code==200
    assert 'HttpOnly' in r.headers['set-cookie']
    return {'Origin':'http://testserver','X-CSRF-Token':r.json()['csrf']}

def test_auth_csrf(client):
    for path in ['config','pairing','status','events']:assert client.get('/api/'+path).status_code==401
    assert client.post('/api/login',json={'username':'admin','password':'bad'}).status_code==403
    h=login(client)
    assert client.patch('/api/config',json={'ai':True},headers={'Origin':'http://testserver'}).status_code==403
    assert client.patch('/api/config',json={'ai':True},headers=h).status_code==200
    assert client.get('/api/config').json()['ai'] is True
    assert client.post('/api/logout',json={},headers=h).status_code==200
    assert client.get('/api/config').status_code==401

def test_settings_validation_secret(client):
    h=login(client)
    assert client.patch('/api/config',json={'ai_key':'fake-test-secret'},headers=h).status_code==200
    c=client.get('/api/config');assert 'fake-test-secret' not in c.text and c.json()['ai_key_configured']
    for p in ({'admins':['abc']},{'cooldown':-1},{'ai_base_url':'http://127.0.0.1/v1'},{'unknown':True},{'ai':'false'}):assert client.patch('/api/config',json=p,headers=h).status_code==422
    assert client.patch('/api/config',json={'ai_key':'','ai':False},headers=h).status_code==200

def test_login_limiter(client):
    for _ in range(5):assert client.post('/api/login',json={'username':'admin','password':'wrong'},headers={'Origin':'http://testserver'}).status_code==401
    assert client.post('/api/login',json={'username':'admin','password':'wrong'},headers={'Origin':'http://testserver'}).status_code==429

def test_controls_headers(client):
    h=login(client)
    for action,status in [('stop','stopped'),('start','demo'),('start','demo')]:assert client.post('/api/bot',json={'action':action},headers=h).json()['status']==status
    assert client.get('/api/status').json()['mode']=='demo'
    assert client.get('/').headers['x-frame-options']=='DENY'
    assert client.get('/static/app.js').status_code==200
    assert client.post('/api/bot',content='x'*33000,headers={**h,'Content-Type':'application/json'}).status_code==413

@pytest.mark.asyncio
async def test_encrypted_persistence(env):
    s=Store(env);await s.open();await s.update({'ai_key':'test-secret','welcome_message':'Halo {user}'})
    row=await(await s.db.execute('SELECT payload FROM config')).fetchone();assert 'test-secret' not in row[0]
    await s.close();s=Store(env);await s.open();assert s.config.ai_key=='test-secret';await s.close()

@pytest.mark.asyncio
async def test_ai_history_contract(env):
    captured=[]
    async def handler(req):
        captured.append(json.loads(req.content));assert req.url.path=='/v1/chat/completions';assert req.headers['Authorization']=='Bearer test-key'
        return httpx.Response(200,json={'choices':[{'message':{'content':'Jawaban'}}]})
    s=Store(env);await s.open();await s.update({'ai':True,'ai_key':'test-key'})
    ai=DattioAI(s,httpx.MockTransport(handler));assert await ai.ask(('chat','one'),'Halo')=='Jawaban'
    await ai.ask(('chat','one'),'Lanjut');assert len(captured[-1]['messages'])==4
    await ai.ask(('chat','two'),'Halo');assert len(captured[-1]['messages'])==2
    ai.clear(('chat','one'));assert ('chat','one') not in ai.history
    await ai.close();await s.close()

@pytest.mark.asyncio
async def test_ai_circuit(env):
    s=Store(env);await s.open();await s.update({'ai':True,'ai_key':'secret'})
    ai=DattioAI(s,httpx.MockTransport(lambda r:httpx.Response(429,text='secret')))
    for _ in range(3):
        with pytest.raises(ValueError,match='AI belum dapat'):await ai.ask('x','hello')
    with pytest.raises(ValueError,match='sibuk'):await ai.ask('x','hello')
    assert not ai.history;await ai.close();await s.close()

def test_native_responses():
    m=Message();m.interactiveResponseMessage.nativeFlowResponseMessage.paramsJSON='{"id":".menu"}';assert text_of(m)=='.menu'
    m=Message();m.listResponseMessage.singleSelectReply.selectedRowID='.ai';assert text_of(m)=='.ai'
    m=Message();m.buttonsResponseMessage.selectedButtonID='.ping';assert text_of(m)=='.ping'
    m=Message();m.interactiveResponseMessage.nativeFlowResponseMessage.paramsJSON='garbage';assert text_of(m)==''

def test_limits_urls():
    t=TTLCache(limit=2);assert t.claim('a',5);assert not t.claim('a',5);t.claim('b',1);t.claim('c',1);assert len(t.items)==2
    assert validate_url('https://youtu.be/abc')
    for url in ['http://localhost/x','https://127.0.0.1/a','https://youtube.com.evil.test/a','https://user@youtube.com/a','file:///etc/passwd']:
        with pytest.raises(ValueError):validate_url(url)

@pytest.mark.asyncio
async def test_menu_payload_fallback():
    sent=[]
    async def send(chat,button):sent.append(await button.prepare_asend(None))
    bot=SimpleNamespace(outgoing=0,store=SimpleNamespace(config=Config()),gate=SimpleNamespace(wait=AsyncMock()),client=SimpleNamespace(send_interactive_message=send),log=lambda _:None)
    ctx=SimpleNamespace(bot=bot,chat_key='a',chat='a',reply=AsyncMock());await menu(ctx,'');assert len(sent[0].interactiveMessage.nativeFlowMessage.buttons)==3
    bot.client.send_interactive_message=AsyncMock(side_effect=RuntimeError());await menu(ctx,'');ctx.reply.assert_awaited_once()

@pytest.mark.asyncio
async def test_duplicate_queue(env):
    s=Store(env);await s.open();b=Bot(s,'demo');b.running=True
    ev=Event();ev.Info.ID='abc';ev.Info.MessageSource.Chat.CopyFrom(JID(User='123',Server='s.whatsapp.net'));ev.Info.MessageSource.Sender.CopyFrom(JID(User='123',Server='s.whatsapp.net'));ev.Message.conversation='.ping'
    await b.receive(None,ev);await b.receive(None,ev);assert b.queue.qsize()==1
    for i in range(250):
        other=Event();other.CopyFrom(ev);other.Info.ID=str(i);await b.receive(None,other)
    assert b.queue.qsize()==250 and b.dropped==1
    await b.close();await s.close()

@pytest.mark.asyncio
async def test_daffo_identity_in_ai_payload(env):
    captured=[]
    async def handler(req):
        captured.append(json.loads(req.content))
        return httpx.Response(200,json={'choices':[{'message':{'content':'Saya adalah Daffo BOT'}}]})
    s=Store(env);await s.open();await s.update({'ai':True,'ai_key':'test-key'})
    ai=DattioAI(s,httpx.MockTransport(handler));await ai.ask('x','siapa kamu?')
    system=captured[-1]['messages'][0]['content']
    assert 'Daffo BOT' in system and 'Lord Daffo' in system and '085648175452' in system
    await ai.close();await s.close()

@pytest.mark.asyncio
async def test_subprocess_timeout():
    import sys
    with pytest.raises(asyncio.TimeoutError):await process(sys.executable,'-c','import time; time.sleep(5)',timeout=.05)

@pytest.mark.asyncio
async def test_supervisor_stops_on_logout(env,monkeypatch):
    import bot.runtime as runtime
    clients=[]
    class Fake:
        def __init__(self,*a):self.handlers={};clients.append(self)
        def event(self,kind):
            def register(fn):self.handlers[kind]=fn
            return register
        def qr(self,fn):pass
        async def connect(self):
            async def run():await self.handlers[runtime.LoggedOutEv](self,None)
            return asyncio.create_task(run())
        async def stop(self):pass
    monkeypatch.setattr(runtime,'NewAClient',Fake)
    s=Store(env);await s.open();b=Bot(s);await b.start()
    await asyncio.wait_for(b.supervisor,1)
    assert b.status=='logged_out' and len(clients)==1
    await b.close();await s.close()

@pytest.mark.asyncio
async def test_supervisor_reconnect_after_task_failure(env,monkeypatch):
    import bot.runtime as runtime
    clients=[]
    class Fake:
        def __init__(self,*a):clients.append(self)
        def event(self,kind):return lambda fn:fn
        def qr(self,fn):pass
        async def connect(self):
            async def run():raise RuntimeError('network')
            return asyncio.create_task(run())
        async def stop(self):pass
    monkeypatch.setattr(runtime,'NewAClient',Fake)
    monkeypatch.setattr(runtime.random,'random',lambda:0)
    s=Store(env);await s.open();b=Bot(s);await b.start()
    await asyncio.sleep(.03);assert b.status=='reconnecting'
    await b.close();assert b.status=='stopped';await s.close()

@pytest.mark.asyncio
async def test_ffmpeg_opus(tmp_path):
    import shutil
    if not shutil.which('ffmpeg'):pytest.skip('ffmpeg unavailable')
    target=tmp_path/'voice.ogg'
    await process('ffmpeg','-nostdin','-v','error','-f','lavfi','-i','sine=frequency=440:duration=0.2','-c:a','libopus','-ar','48000','-ac','1',str(target))
    assert target.read_bytes().startswith(b'OggS') and b'OpusHead' in target.read_bytes()
