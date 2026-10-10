"""Run once locally or via docker compose run --rm bot python scripts/setup.py."""
import getpass
import os
from pathlib import Path
from argon2 import PasswordHasher
from cryptography.fernet import Fernet

def main():
    target=Path('.env')
    if target.exists():raise SystemExit('.env sudah ada; simpan salinan sebelum mengganti kredensial. Jangan mengganti ENCRYPTION_KEY pada instalasi aktif.')
    username=input('Username admin [admin]: ').strip() or 'admin'
    password=getpass.getpass('Password admin (minimal 12 karakter): ')
    if len(password)<12:raise SystemExit('Password terlalu pendek.')
    if password!=getpass.getpass('Ulangi password: '):raise SystemExit('Password tidak cocok.')
    origin=input('URL dashboard [http://localhost:8000]: ').strip() or 'http://localhost:8000'
    if not origin.startswith(('https://','http://localhost:','http://127.0.0.1:')):raise SystemExit('Gunakan HTTPS untuk akses selain localhost.')
    if any(x in username+origin for x in "\r\n'\""):raise SystemExit('Karakter tidak valid.')
    content=f"ADMIN_USERNAME={username}\nADMIN_PASSWORD_HASH='{PasswordHasher().hash(password)}'\nENCRYPTION_KEY={Fernet.generate_key().decode()}\nPUBLIC_ORIGIN={origin.rstrip('/')}\nCOOKIE_SECURE={'true' if origin.startswith('https:') else 'false'}\nBOT_MODE=whatsapp\nDATA_DIR=data\nHOST=0.0.0.0\nPORT=8000\nAI_ALLOWED_HOSTS=bandelbanget.xyz\n"
    with target.open('x') as f:f.write(content)
    os.chmod(target,0o600)
    print('Konfigurasi dibuat. Jalankan bot, lalu login dashboard untuk menautkan WhatsApp.')
if __name__=='__main__':main()
