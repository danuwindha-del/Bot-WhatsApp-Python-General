import os,sys,tempfile
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
os.environ.update(ADMIN_PASSWORD_HASH=PasswordHasher().hash('Ui-test-only-password'),ENCRYPTION_KEY=Fernet.generate_key().decode(),PUBLIC_ORIGIN='http://127.0.0.1:8765',COOKIE_SECURE='false',BOT_MODE='demo',DATA_DIR=tempfile.mkdtemp(prefix='daffo-ui-'))
from web.app import create_app
import uvicorn
try:uvicorn.run(create_app(),host='127.0.0.1',port=8765,access_log=False)
finally:
 import shutil
 shutil.rmtree(os.environ['DATA_DIR'],ignore_errors=True)
