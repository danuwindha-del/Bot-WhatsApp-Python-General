import base64
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from PIL import Image
from neonize.proto.Neonize_pb2 import JID, Message as Event
from neonize.proto.waE2E.WAWebProtobufsE2E_pb2 import Message

from bot.ai import DaffoAI
from bot.config import Store
from bot.runtime import Bot
from bot.training import Dataset, Document, Example, Evaluation, Conflict, retrieve
from bot.vision import image_data_url, image_message, MAX_IMAGE_BYTES
from test_system import env, client, login


def picture():
    buf=io.BytesIO()
    Image.new('RGB',(64,32),'green').save(buf,format='PNG')
    return buf.getvalue()


def test_image_normalization_and_limits():
    url=image_data_url(picture())
    data=base64.b64decode(url.split(',')[1])
    with Image.open(io.BytesIO(data)) as img:
        assert img.format=='JPEG' and img.size==(64,32) and not img.getexif()
    for data in (b'',b'not an image',b'x'*(MAX_IMAGE_BYTES+1)):
        with pytest.raises(ValueError):image_data_url(data)


def test_retrieval_chunks_and_disabled_documents():
    docs=Dataset(documents=[Document(title='Pengiriman',content='Pesanan dikirim dalam 3 hari kerja. Ongkir gratis.',tags='kurir'),Document(title='Rahasia',content='Pengiriman tersembunyi',enabled=False)])
    result=retrieve(docs,'Berapa lama pengiriman kurir?')
    assert len(result)==1 and result[0]['title']=='Pengiriman' and '3 hari' in result[0]['text']
    assert retrieve(docs,'astronomi bintang')==[]


@pytest.mark.asyncio
async def test_publish_revision_rollback_and_persistence(env):
    store=Store(env);await store.open();t=store.training
    draft=Dataset(documents=[Document(title='Pengiriman',content='Pengiriman 3 hari')],examples=[Example(question='Pengiriman',answer='Tentu, 3 hari ya.')])
    await t.save(draft,0)
    assert not t.context('pengiriman')[1] and t.context('pengiriman',True)[1]
    with pytest.raises(Conflict):await t.save(draft,0)
    first=await t.publish(1,'Pertama');version=first['active_version']
    draft2=draft.model_copy(deep=True);draft2.documents[0].content='Pengiriman 7 hari'
    await t.save(draft2,2);await t.publish(3,'Kedua')
    assert '7 hari' in t.context('pengiriman')[0]
    await t.rollback(version,4)
    assert '3 hari' in t.context('pengiriman')[0] and '7 hari' in t.context('pengiriman',True)[0]
    await store.close();store=Store(env);await store.open()
    try:
        assert store.training.active_version==version and store.training.revision==5
        assert '3 hari' in store.training.context('pengiriman')[0]
    finally:await store.close()


@pytest.mark.asyncio
async def test_multimodal_provider_contract_and_history_privacy(env):
    store=Store(env);await store.open();await store.update({'ai_key':'test','ai_vision_model':'vision-model'})
    captured=[]
    def handler(req):
        payload=json.loads(req.content);captured.append(payload)
        return httpx.Response(200,json={'choices':[{'message':{'content':'Gambar hijau.'}}]})
    ai=DaffoAI(store,httpx.MockTransport(handler))
    try:
        assert await ai.ask('user','Jelaskan',image=picture())=='Gambar hijau.'
        payload=captured[0];assert payload['model']=='vision-model'
        assert payload['messages'][-1]['content'][1]['image_url']['url'].startswith('data:image/jpeg;base64,')
        assert 'base64' not in json.dumps(ai.history) and ai.vision_requests==1
        await ai.ask('user','Jelaskan lagi')
        assert captured[1]['model']==store.config.ai_model and all(isinstance(m['content'],str) for m in captured[1]['messages'])
        await store.update({'ai_vision':False})
        with pytest.raises(ValueError,match='dinonaktifkan'):await ai.ask('user','lihat',image=picture())
    finally:await ai.close();await store.close()


@pytest.mark.asyncio
async def test_vision_rejection_does_not_silently_answer_without_image(env):
    store=Store(env);await store.open();await store.update({'ai_key':'test'})
    ai=DaffoAI(store,httpx.MockTransport(lambda r:httpx.Response(400,json={'error':'vision unsupported'})))
    try:
        with pytest.raises(ValueError,match='menolak gambar'):await ai.ask('u','lihat',image=picture())
        assert ai.vision_supported is False and not ai.history and ai.requests==0
    finally:await ai.close();await store.close()


@pytest.mark.asyncio
async def test_published_knowledge_is_used_in_ai_requests(env):
    store=Store(env);await store.open();await store.update({'ai_key':'test'})
    t=store.training
    await t.save(Dataset(documents=[Document(title='Garansi',content='Garansi produk berlaku 2 tahun.')]),0)
    captured=[]
    def handler(req):
        captured.append(json.loads(req.content)['messages'][0]['content'])
        return httpx.Response(200,json={'choices':[{'message':{'content':'Jawaban'}}]})
    ai=DaffoAI(store,httpx.MockTransport(handler))
    try:
        await ai.ask('a','Garansi produk?');assert '2 tahun' not in captured[-1]
        await ai.ask('b','Garansi produk?',knowledge_draft=True);assert '2 tahun' in captured[-1]
        await t.publish(1,'Garansi');await ai.ask('c','Garansi produk?');assert '2 tahun' in captured[-1]
    finally:await ai.close();await store.close()


def image_event(text='',group=False):
    event=Event();event.Info.ID='image-1'
    event.Info.MessageSource.Chat.CopyFrom(JID(User='123',Server='g.us' if group else 's.whatsapp.net'))
    event.Info.MessageSource.Sender.CopyFrom(JID(User='456',Server='s.whatsapp.net'))
    event.Message.imageMessage.caption=text;event.Message.imageMessage.fileLength=len(picture())
    return event


@pytest.mark.asyncio
async def test_whatsapp_image_routing_and_group_policy(env):
    store=Store(env);await store.open();await store.update({'ai_key':'test'})
    bot=Bot(store,'demo');await bot.start();bot.send=AsyncMock();bot.ai.ask=AsyncMock(return_value='Terlihat hijau')
    bot.client=SimpleNamespace(download_any=AsyncMock(return_value=picture()))
    try:
        await bot.handle(image_event())
        bot.client.download_any.assert_awaited_once();assert bot.ai.ask.call_args.kwargs['image']==picture()
        bot.ai.ask.reset_mock();await store.update({'ai_group_mode':'mention'})
        await bot.handle(image_event('Jelaskan',True));bot.ai.ask.assert_not_awaited()
        await bot.handle(image_event('Daffo jelaskan',True));bot.ai.ask.assert_awaited_once()
        bot.ai.ask.reset_mock();await store.update({'ai_private':False})
        await bot.handle(image_event());bot.ai.ask.assert_not_awaited()
        await bot.handle(image_event('.lihat apa ini?'));bot.ai.ask.assert_awaited_once()
        assert {'lihat','ocr','vision'}.issubset(bot.router)
    finally:await bot.close();await store.close()


def test_quoted_images_and_view_once_privacy():
    quoted=Message();quoted.extendedTextMessage.text='.lihat'
    quoted.extendedTextMessage.contextInfo.quotedMessage.imageMessage.caption='foto'
    assert image_message(quoted) is None
    assert image_message(quoted,True).HasField('imageMessage')
    once=Message();once.viewOnceMessage.message.imageMessage.caption='privat'
    assert image_message(once,True) is None


def test_studio_api_auth_csrf_conflicts_and_evaluation(client):
    assert client.get('/api/training').status_code==401
    h=login(client);state=client.get('/api/training').json();assert state['revision']==0
    profile=state['draft']['profile']
    assert client.put('/api/training/profile',json={'revision':0,'profile':profile},headers={'Origin':'http://testserver'}).status_code==403
    assert client.put('/api/training/profile',json={'revision':0,'profile':profile}).status_code==403
    r=client.post('/api/training/documents',json={'revision':0,'document':{'title':'Pengiriman','content':'Pengiriman gratis dalam 3 hari.'}},headers=h)
    assert r.status_code==200;r=r.json();doc_id=r['draft']['documents'][0]['id']
    assert client.post('/api/training/documents',json={'revision':0,'document':{'title':'x','content':'y'}},headers=h).status_code==409
    preview=client.post('/api/training/preview',json={'prompt':'Pengiriman?'},headers=h)
    assert preview.status_code==200 and preview.json()['sources'][0]['id']==doc_id and preview.json()['answer'] is None
    assert client.post('/api/training/evaluate',json={},headers=h).status_code==422
    r=client.post('/api/training/evaluations',json={'revision':1,'evaluation':{'question':'Pengiriman?','expected':'gratis, 3 hari'}},headers=h)
    assert r.status_code==200
    result=client.post('/api/training/evaluate',json={},headers=h).json()
    assert result['passed']==1 and result['total']==1 and result['mode']=='retrieval'
    published=client.post('/api/training/publish',json={'revision':2,'label':'Versi uji'},headers=h)
    assert published.status_code==200 and published.json()['active_version']
    assert client.post('/api/training/import',json={'revision':3,'dataset':{'api_key':'oops'}},headers=h).status_code==422
    assert client.request('DELETE','/api/training/documents/'+doc_id,json={'revision':3},headers=h).status_code==200
    assert client.get('/api/training').json()['active_documents']==1


def test_dashboard_vision_validation(client):
    h=login(client)
    assert client.post('/api/ai/test',json={'prompt':'lihat','image_base64':'invalid!!'},headers=h).status_code==422
    # Valid image reaches the real AI path, which reports missing credentials.
    r=client.post('/api/ai/test',json={'prompt':'lihat','image_base64':base64.b64encode(picture()).decode()},headers=h)
    assert r.status_code==422 and 'API key' in r.json()['detail']


def test_ephemeral_caption_is_preserved():
    from bot.context import text_of
    message=Message();message.ephemeralMessage.message.imageMessage.caption='.lihat baca tulisan'
    assert text_of(message)=='.lihat baca tulisan'
    assert image_message(message).HasField('imageMessage')


def test_draft_saves_do_not_reset_live_memory(client):
    h=login(client);ai=client.app.state.bot.ai
    ai.history['live-chat']=(0,[{'role':'user','content':'halo'}])
    assert client.post('/api/training/documents',json={'revision':0,'document':{'title':'FAQ','content':'Jawaban'}},headers=h).status_code==200
    assert 'live-chat' in ai.history
    assert client.post('/api/training/publish',json={'revision':1},headers=h).status_code==200
    assert not ai.history


def test_training_import_duplicate_ids_and_unicode_payload(client):
    h=login(client)
    d=Document(title='Unicode',content='漢字'*6000).model_dump()
    assert client.post('/api/training/documents',json={'revision':0,'document':d},headers=h).status_code==200
    dataset=Dataset(documents=[Document(**d),Document(**d)]).model_dump()
    assert client.post('/api/training/import',json={'revision':1,'dataset':dataset},headers=h).status_code==422
    assert client.get('/api/training').json()['revision']==1


@pytest.mark.asyncio
async def test_versions_are_bounded_to_twenty(env):
    store=Store(env);await store.open()
    try:
        for revision in range(22):await store.training.publish(revision,'Versi '+str(revision))
        state=await store.training.overview()
        assert len(state['versions'])==20 and state['revision']==22
    finally:await store.close()
