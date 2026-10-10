# Upgrade VPS/systemd dari v3 ke v3.1

Paket ini belum terpasang di VPS Anda. Semua langkah di bawah dilakukan pada VPS, bukan dengan mengirim command ke chat WhatsApp.

## 1. Temukan direktori aktif

```bash
sudo systemctl cat daffo-bot.service
```

Catat `WorkingDirectory` dan `ExecStart`. Gunakan direktori yang benar; jangan mengasumsikan `/opt/daffo-botz` jika instalasi Anda berbeda.

## 2. Hentikan layanan dan cadangkan

```bash
sudo systemctl stop daffo-bot.service
```

Cadangkan **seluruh folder lama** ke folder terpisah, termasuk `.env`, `data/`, serta berkas SQLite `-wal`/`-shm` jika masih ada. Jangan menghapus folder lama atau menjalankan dua bot dengan sesi yang sama.

## 3. Ekstrak paket baru ke folder baru

Salin `.env` lama dan seluruh folder `data/` ke folder baru. Jika `.env` memakai `DATA_DIR` absolut, perbarui ke direktori salinan yang baru agar backup tidak ikut berubah.

**Jangan jalankan `scripts/setup.py` lagi pada instalasi yang sudah memiliki `.env`.** `ENCRYPTION_KEY` harus tetap sama agar API key tersimpan bisa dibaca.

Dari folder baru:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.lock
```

Pastikan FFmpeg dan libmagic tersedia. Sesuaikan `WorkingDirectory` dan `ExecStart` pada unit systemd ke folder baru dan Python `.venv/bin/python` baru. Pertahankan User/Group layanan yang sesuai dengan pemilik `.env` serta `data/`.

```bash
sudo systemctl daemon-reload
sudo systemctl start daffo-bot.service
sudo systemctl status daffo-bot.service --no-pager
sudo journalctl -u daffo-bot.service -n 100 --no-pager
```

## 4. Pengaturan setelah upgrade

- Login dashboard dengan akun yang sama; refresh penuh browser agar JavaScript terbaru dimuat.
- Features → Cooldown: **0** untuk tidak mengabaikan pesan beruntun akibat cooldown input. Pacing pengiriman tetap berlaku.
- Jeda kirim global/per chat: mulai dari **0,3 / 0,7 detik**. Tingkatkan jika grup sangat ramai atau WhatsApp memberi batas.
- Daffo AI → **AI tools**, **Ingat hasil command**, dan mode balas private/group sesuai kebutuhan.
- Timeout AI awal **25 detik**. Uji AI di dashboard; tes menggunakan kuota provider.
- System → Periksa sistem. Status WhatsApp harus `connected`; `/healthz` hanya menunjukkan web hidup.
- Uji `.ping`, `.calc 12*8`, `.calc 15%*200000`, `.wiki Indonesia`, `.tebakkata` → `.nyerah`, dan `.menu` di chat uji.
- Uji `.setdesc`, `.revoke`, dan moderasi di grup uji tempat bot memiliki hak admin. Revoke mengganti tautan undangan lama.

## Perintah layanan

```bash
sudo systemctl restart daffo-bot.service
sudo systemctl stop daffo-bot.service
sudo systemctl start daffo-bot.service
sudo journalctl -u daffo-bot.service -f
```

Jika perlu rollback: hentikan layanan baru, kembalikan unit ke **folder backup lama beserta datanya**, kemudian daemon-reload dan start. Konfigurasi versi 3.1 memiliki field baru yang tidak dikenali versi 3.0; jangan menunjuk versi lama ke database konfigurasi yang sudah diperbarui.
