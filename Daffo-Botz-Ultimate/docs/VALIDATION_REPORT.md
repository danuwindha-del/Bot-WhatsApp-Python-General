# Validasi v3.2

- 71 tes Python lulus, termasuk kontrak provider multimodal, knowledge injection, routing gambar, mode grup, quoted/ephemeral, view-once, batas upload, CSRF, konflik revisi, persistensi, versi, dan dataset.
- Paket release diuji agar dataset legacy tetap masuk, sementara data runtime, rahasia, dependensi, dan screenshot dikecualikan.
- Suite UI happy-dom lulus (27 permintaan).
- Browser Chromium lulus: login, profil, CRUD dokumen, contoh, retrieval preview, evaluasi, publish/rollback, reload, import/export, file gambar, error API key kosong, tema terang/gelap dan mobile tanpa overflow horizontal.
- Satu peringatan deprecation berasal dari Starlette TestClient/httpx; tidak ada kegagalan tes.
- Provider vision sungguhan dan pairing akun WhatsApp belum diuji. Kontrak provider dan alur WhatsApp diuji menggunakan transport/client tiruan. Screenshot berasal dari server demo dengan data pengujian.

# Validasi Daffo-Botz 3.1 — 7 Oktober 2026

## Hasil

**56 pengujian Python lulus** dengan dependency Neonize 0.5.2 dan Python 3.12 yang benar-benar diinstal. Satu warning deprecation dari Starlette TestClient/httpx; tidak ada tes gagal.

- 15 variasi hitungan: tambah, kurang, kali, bagi, pangkat, persen, desimal, tanda kurung dan fungsi.
- Penolakan ekspresi kode, angka/pangkat berlebihan, pembagian nol, dan input tidak valid.
- Wikipedia search/extract/cache dan error provider melalui HTTPX MockTransport.
- AI tool round-trip: hasil hitungan nyata masuk sebagai hasil tool sebelum jawaban model.
- Provider menolak tools → fallback chat; AI circuit breaker; history terisolasi.
- Reset history saat request berjalan tidak memulihkan history yang sudah dihapus.
- Command reply tidak menunggu AI; konteks command tersedia untuk pertanyaan lanjutan.
- Perintah cepat tetap selesai saat empat worker AI sengaja ditahan; fairness FIFO per lane dan batas antrean diuji.
- Game lintas handler, `.nyerah`, tebak bendera, KBBI, feature toggle runtime.
- Signature setdesc/revoke sesuai Neonize; eksekusi memakai AsyncMock (tidak mengubah grup nyata).
- Strike limit moderasi dan saldo economy/deposit/withdraw.
- Login/session, CSRF/Origin, validasi konfigurasi, key terenkripsi, ekspor tanpa key.
- Menu protobuf asli, reconnect/logged-out menggunakan mock, timeout subprocess, FFmpeg menghasilkan Opus.

## Dashboard

**Uji DOM menggunakan happy-dom + API FastAPI lokal mode demo lulus**, 26 request, tanpa error JavaScript yang tertangkap. Mencakup login, navigasi tab, simpan AI/performance settings, switch fitur, pencarian command, diagnostik, tampilan error AI tanpa key, reset memory, penolakan kirim ketika WhatsApp belum terhubung, start/stop/restart dan logout.

`node --check web/static/app.js` dan compile semua Python lulus. Pemeriksaan DOM ini bukan rendering browser penuh. Instalasi Chromium tidak berhasil di lingkungan validasi, sehingga screenshot, layout pada handset, clipboard/download browser nyata dan visual QR belum diuji.

## Batas pengujian

Tidak memakai akun WhatsApp, sesi pengguna, atau API key berbayar. Tidak mengirim pesan nyata. Respons Wikipedia/AI pada tes menggunakan mock; akses produksi ke Wikipedia/provider dan kualitas jawaban model perlu diuji dari VPS. Build Docker tidak dijalankan. Waktu respons WhatsApp nyata atau jaminan delay nol tidak dapat disimpulkan dari tes lokal.

## Menjalankan kembali

Dari root proyek dengan dependency terpasang:

```bash
python -m pytest -q
python -m compileall -q bot legacy web main.py
node --check web/static/app.js
```

Untuk uji dashboard tanpa browser penuh (Node.js, port 8765 harus tersedia):

```bash
npm install --prefix tests/ui
python tests/ui/run.py
```

Uji dashboard menjalankan server demo dengan password khusus uji dan direktori data sementara. Tidak membaca akun `.env` produksi atau menautkan WhatsApp. Berkas database sementara dibersihkan ketika server dihentikan normal.
