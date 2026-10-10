# Deployment

## Non-Docker

Ikuti README untuk instalasi baru, docs/UPGRADE.md untuk upgrade systemd. Jalankan satu proses Uvicorn/WhatsApp per direktori sesi. Jangan menambah Uvicorn worker; setiap worker akan membuat client bot sendiri.

## Docker Compose

Gunakan Python lokal untuk setup awal setelah memasang dependensi, atau siapkan `.env` secara aman. `scripts/setup.py` menghasilkan file mode 600. Container menggunakan UID 10001, sehingga file harus dapat dibaca UID tersebut:

```bash
sudo chown 10001:10001 .env
sudo chmod 600 .env
docker compose up -d --build
docker compose logs -f
```

Jika memakai Docker rootless/user namespace, sesuaikan pemetaan UID host. Jangan membuat `.env` dapat dibaca semua pengguna. Direktori `/app/data` memakai named volume `bot_data`; pertahankan volume saat upgrade. Jangan menjalankan `docker compose down -v` untuk upgrade biasa.

Paket tidak mengecualikan `legacy/` dari build. Runtime memerlukan modul dan dataset di sana. Container: non-root, read-only root filesystem, tmpfs 1 GiB, cap_drop ALL, resource limits. tmpfs dan proses konversi tetap dihitung dalam batas memori container; unduhan besar dapat memerlukan penyesuaian kapasitas VPS.

## HTTPS / domain

Ganti domain contoh pada Caddyfile dan arahkan proxy ke `127.0.0.1:8000`. `PUBLIC_ORIGIN` harus tepat sama dengan alamat browser, termasuk skema dan port, tanpa slash terakhir. Untuk HTTPS gunakan `COOKIE_SECURE=true`. Untuk SSH tunnel `http://localhost:8000`, gunakan origin tersebut dan `COOKIE_SECURE=false`.

## Backup

Hentikan bot sebelum menyalin SQLite. Simpan seluruh `data/` dan `.env` di tempat aman. Jangan mengubah ENCRYPTION_KEY saat memindahkan instalasi. Session WhatsApp tetap berlaku hanya jika belum dicabut WhatsApp.

## Troubleshooting

- **403 Origin:** cocokkan PUBLIC_ORIGIN; restart proses setelah mengubah `.env`.
- **Login berulang:** cookie Secure memerlukan HTTPS.
- **429 login:** tunggu lima menit. Di balik proxy, pembatasan bisa dibagi oleh semua admin melalui IP proxy.
- **AI lambat:** lihat AI latency; kurangi panjang jawaban/max tokens jika perlu, pilih model provider yang lebih cepat, atur timeout. Bot tidak dapat mempercepat server model.
- **Tools tidak didukung:** diagnostik AI menandai dukungan provider; chat biasa dan command langsung tetap berfungsi.
- **Media gagal:** pastikan FFmpeg ada, URL didukung, kapasitas disk cukup; platform sumber dapat membatasi unduhan.
- **Fitur Provider:** belum ada integrasi native, bukan fitur yang sudah teruji menghasilkan media.
- **Tidak ada QR:** sesi mungkin sudah connected; scan hanya jika bot memang meminta pairing.
