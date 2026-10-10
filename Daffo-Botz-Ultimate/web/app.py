import asyncio
import json
import os
import secrets
import time
from collections import OrderedDict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, ConfigDict

from bot.config import Store
from bot.runtime import Bot
from bot.assistant_tools import Toolbox
from bot.vision import decode_image
import shutil
import platform
import uuid

STATIC = Path(__file__).parent / 'static'


class Credentials(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=256)


class AITest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    image_base64: str | None = Field(default=None, max_length=6990508)


class Change(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: str


class SendMessage(BaseModel):
    model_config = ConfigDict(extra='forbid')
    target: str = Field(min_length=3, max_length=100)
    text: str = Field(min_length=1, max_length=5000)


class GroupAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    jid: str = Field(min_length=5, max_length=100)
    action: str = Field(min_length=2, max_length=20)
    text: str = Field(default='', max_length=5000)


def create_app():
    sessions = OrderedDict()
    operation_lock = asyncio.Lock()
    attempts = OrderedDict()
    verify_slots = asyncio.Semaphore(2)
    secure = os.getenv('COOKIE_SECURE', 'true').lower() == 'true'
    origin = os.getenv('PUBLIC_ORIGIN', 'https://localhost').rstrip('/')
    password_hash = os.environ.get('ADMIN_PASSWORD_HASH', '')
    if not password_hash.startswith('$argon2'):
        raise RuntimeError('Jalankan scripts/setup.py untuk membuat .env aman.')

    @asynccontextmanager
    async def lifespan(app):
        store = Store(os.getenv('DATA_DIR', 'data'))
        await store.open()
        bot = Bot(store, os.getenv('BOT_MODE', 'whatsapp'))
        app.state.store = store
        app.state.bot = bot
        await bot.start()
        try:
            yield
        finally:
            await bot.close()
            await store.close()

    app = FastAPI(title='Daffo Control Center', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware('http')
    async def security(request, call_next):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            if request.headers.get('origin') != origin:
                return JSONResponse({'detail': 'Origin tidak valid'}, status_code=403)
            if 'application/json' not in request.headers.get('content-type', ''):
                return JSONResponse({'detail': 'JSON diperlukan'}, status_code=415)
            limit = 8 * 1024 * 1024 if request.url.path == '/api/ai/test' else 1024 * 1024 if request.url.path == '/api/training/import' else 65536 if request.url.path == '/api/training/documents' else 32768
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > limit:
                    return JSONResponse({'detail': 'Payload terlalu besar'}, status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        if secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response

    def session(request: Request):
        token = request.cookies.get('daffo_session', '')
        entry = sessions.get(token)
        if not entry or entry['expires'] < time.monotonic():
            sessions.pop(token, None)
            raise HTTPException(401, 'Silakan login')
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE') and not secrets.compare_digest(request.headers.get('x-csrf-token', ''), entry['csrf']):
            raise HTTPException(403, 'CSRF tidak valid')
        return entry

    @app.get('/')
    async def index():
        return FileResponse(STATIC / 'index.html')

    app.mount('/static', StaticFiles(directory=STATIC), name='static')

    @app.get('/healthz')
    async def health():
        return {'ok': True, 'service': 'Daffo-Botz'}

    @app.post('/api/login')
    async def login(data: Credentials, request: Request):
        now = time.monotonic()
        ip = request.client.host
        bucket = attempts.setdefault(ip, deque())
        attempts.move_to_end(ip)
        while len(attempts) > 1000:
            attempts.popitem(last=False)
        while bucket and bucket[0] < now - 300:
            bucket.popleft()
        if len(bucket) >= 5:
            raise HTTPException(429, 'Tunggu 5 menit sebelum mencoba lagi')
        bucket.append(now)
        async with verify_slots:
            try:
                valid = await asyncio.to_thread(PasswordHasher().verify, password_hash, data.password)
            except VerificationError:
                valid = False
        if not valid or not secrets.compare_digest(data.username, os.getenv('ADMIN_USERNAME', 'admin')):
            raise HTTPException(401, 'Username atau password salah')
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        sessions[token] = {'csrf': csrf, 'expires': now + 28800, 'test_lock': asyncio.Lock()}
        while len(sessions) > 20:
            sessions.popitem(last=False)
        result = JSONResponse({'csrf': csrf})
        result.set_cookie('daffo_session', token, httponly=True, secure=secure, samesite='strict', max_age=28800, path='/')
        return result

    @app.get('/api/session')
    async def me(auth=Depends(session)):
        return {'csrf': auth['csrf']}

    @app.post('/api/logout')
    async def logout(request: Request, auth=Depends(session)):
        sessions.pop(request.cookies.get('daffo_session'), None)
        response = JSONResponse({'ok': True})
        response.delete_cookie('daffo_session')
        return response

    @app.get('/api/config')
    async def config(auth=Depends(session)):
        return app.state.store.public()

    @app.patch('/api/config')
    async def update(request: Request, auth=Depends(session)):
        data = await request.json()
        if not isinstance(data, dict):
            raise HTTPException(422, 'Objek JSON diperlukan')
        try:
            result = await app.state.store.update(data)
        except (ValidationError, ValueError):
            raise HTTPException(422, 'Pengaturan tidak valid. Periksa nilai, endpoint AI, dan batas panjang.') from None
        if any(k.startswith('ai') for k in data):
            app.state.bot.ai.clear()
            app.state.bot.ai.reset_provider()
        app.state.bot.log('Admin memperbarui konfigurasi dari Daffo Control Center.')
        return result

    @app.get('/api/status')
    async def status(auth=Depends(session)):
        return app.state.bot.snapshot()

    @app.get('/api/pairing')
    async def pairing(auth=Depends(session)):
        bot = app.state.bot
        return {'qr': bot.qr_image if time.monotonic() < bot.qr_expires else None, 'status': bot.status}

    @app.post('/api/bot')
    async def control(data: Change, auth=Depends(session)):
        if operation_lock.locked():raise HTTPException(409,'Kontrol bot sedang diproses.')
        async with operation_lock:
            if data.action == 'start':await app.state.bot.start()
            elif data.action == 'stop':await app.state.bot.stop()
            elif data.action == 'restart':await app.state.bot.restart()
            else:raise HTTPException(422,'Gunakan start, stop, atau restart')
        return {'status': app.state.bot.status}

    @app.get('/api/commands')
    async def commands(auth=Depends(session)):
        return {'commands': sorted(app.state.bot.router), 'count': len(app.state.bot.router), 'catalog': app.state.bot.command_catalog()}

    @app.post('/api/message')
    async def send_message(data: SendMessage, auth=Depends(session)):
        try:
            await app.state.bot.web_send(data.target, data.text)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        except Exception:
            raise HTTPException(502, 'WhatsApp menolak operasi. Periksa koneksi dan izin admin bot.') from None
        app.state.bot.log('Admin mengirim satu pesan dari dashboard.')
        return {'ok': True}

    @app.post('/api/groups/refresh')
    async def refresh_groups(auth=Depends(session)):
        groups = await app.state.bot.refresh_groups()
        return {'groups': groups}

    @app.post('/api/group-action')
    async def group_action(data: GroupAction, auth=Depends(session)):
        try:
            result = await app.state.bot.web_group_action(data.jid, data.action, data.text)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None
        except Exception:
            raise HTTPException(502, 'WhatsApp menolak operasi. Periksa koneksi dan izin admin bot.') from None
        app.state.bot.log('Admin menjalankan kontrol grup dari dashboard.')
        return {'ok': True, 'result': result}

    @app.post('/api/ai/clear')
    async def clear_ai(auth=Depends(session)):
        app.state.bot.ai.clear()
        app.state.bot.log('Admin membersihkan memori Daffo AI.')
        return {'ok': True}

    @app.get('/api/diagnostics')
    async def diagnostics(auth=Depends(session)):
        bot=app.state.bot;cfg=app.state.store.config
        checks=[
            {'name':'WhatsApp','ok':bot.status=='connected','detail':bot.status},
            {'name':'FFmpeg','ok':bool(shutil.which('ffmpeg')),'detail':'Media conversion'},
            {'name':'AI key','ok':bool(cfg.ai_key),'detail':'Tersimpan terenkripsi' if cfg.ai_key else 'Belum diisi'},
            {'name':'AI aktif','ok':cfg.ai,'detail':cfg.ai_model},
            {'name':'Feature pack','ok':cfg.legacy_features,'detail':'Aktif' if cfg.legacy_features else 'Nonaktif'},
            {'name':'Database','ok':True,'detail':'SQLite terbuka'},
            {'name':'Origin dashboard','ok':True,'detail':origin},
            {'name':'Cookie HTTPS','ok':secure or origin.startswith(('http://localhost','http://127.0.0.1','http://testserver')),'detail':'Secure' if secure else 'Local HTTP'},
        ]
        return {'checks':checks,'version':'3.2','python':platform.python_version(),'ai':bot.ai.stats()}

    @app.post('/api/ai/test')
    async def test_ai(data: AITest, auth=Depends(session)):
        if auth['test_lock'].locked():raise HTTPException(429,'Satu uji AI masih berjalan.')
        key=('dashboard',uuid.uuid4().hex)
        async with auth['test_lock']:
            try:
                started=time.monotonic()
                answer=await app.state.bot.ai.ask(key,data.prompt,'Uji AI admin. Hanya tool baca saja. Tidak terhubung dengan chat WhatsApp.',Toolbox(app.state.bot), image=decode_image(data.image_base64) if data.image_base64 is not None else None)
                return {'answer':answer,'latency_ms':round((time.monotonic()-started)*1000),'ai':app.state.bot.ai.stats()}
            except ValueError as exc:raise HTTPException(422,str(exc)) from None
            finally:app.state.bot.ai.clear(key)

    @app.get('/api/config/export')
    async def export_config(auth=Depends(session)):
        data=app.state.store.public();data.pop('ai_key_configured',None)
        return JSONResponse(data,headers={'Content-Disposition':'attachment; filename="daffo-settings.json"'})

    @app.get('/api/events')
    async def events(request: Request, auth=Depends(session)):
        token = request.cookies.get('daffo_session')

        async def stream():
            while token in sessions and auth['expires'] > time.monotonic():
                if await request.is_disconnected():
                    break
                yield 'data: ' + json.dumps(app.state.bot.snapshot()) + '\n\n'
                await asyncio.sleep(2)

        return StreamingResponse(stream(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})

    from web.training_api import register_training
    register_training(app,session)
    return app
