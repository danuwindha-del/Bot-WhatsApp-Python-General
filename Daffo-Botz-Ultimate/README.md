# Daffo-Botz 3.2 — Vision & Training Studio

Pembaruan untuk proyek Daffo-Botz Ultimate v3. Identitas bot tetap **Daffo BOT — dibuat oleh Lord Daffo, 085648175452**.


Dashboard baru dengan desain hijau alami, sidebar, tampilan responsif, dan tema terang/gelap. Source proyek sekarang tersedia langsung untuk pengembangan; paket ZIP lama tetap dipertahankan.

## Baru di 3.2

- **Vision WhatsApp:** gambar dengan caption pertanyaan bisa dianalisis otomatis. Balas gambar menggunakan `.lihat` atau `.ocr`. Menggunakan API key/endpoint AI yang sudah dikonfigurasi; isi model vision terpisah bila diperlukan.
- **Vision Lab:** unggah gambar, pilih prompt deskripsi/OCR/produk, dan uji tanpa mengirim pesan WhatsApp.
- **Studio Pelatihan:** profil respons, tujuan, prinsip, pengetahuan, tag, contoh tanya-jawab, pencarian potongan relevan, simulasi, dan pengujian cakupan frasa wajib.
- **Versi pengetahuan:** draft terpisah dari versi aktif, publikasi, 20 versi terakhir, pemulihan versi, konflik revisi, serta ekspor/impor dataset.
- **Pengembangan:** tes backend serta regresi UI dengan happy-dom dan browser Chromium.

Pelatihan menggunakan retrieval pengetahuan dan contoh jawaban dalam konteks model, **bukan fine-tuning bobot model**. Tidak ada model lokal atau API key gratis yang disertakan. Model utama atau model vision perlu mendukung input gambar. Gambar yang diberikan diteruskan ke provider AI yang dipilih, dibatasi 5 MB/20 MP, diperkecil, dan metadata dihapus. Gambar mentah tidak disimpan dalam memori AI. Media sekali lihat tidak diproses.

Panduan lengkap: [Vision & Studio Pelatihan](docs/VISION_TRAINING.md).

### Validasi pengembangan

Dari direktori source, dengan Python 3.12, FFmpeg, libmagic dan Node 20+:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
npm --prefix tests/ui ci --ignore-scripts --no-audit --no-fund
.venv/bin/python -m pytest -q
.venv/bin/python tests/ui/run.py
```

Playwright dipasang melalui lockfile UI. Tes browser tambahan memerlukan Chromium (gunakan `CHROMIUM_PATH` jika bukan `/usr/bin/chromium`):

```bash
.venv/bin/python tests/ui/browser_run.py
```

Port 8765 harus bebas untuk runner UI. Server demo memakai konfigurasi sementara dan hanya bind loopback. Screenshot pengujian tersimpan di `.artifacts/`; jangan gunakan akun uji untuk deployment. Dashboard demo manual: `.venv/bin/python tests/ui/server.py`.

Untuk deployment nyata, jalankan `.venv/bin/python scripts/setup.py` secara aman, pertahankan `.env` dan `data/` yang sudah ada, lalu `.venv/bin/python main.py`. Jangan mencetak atau mengirim rahasia ke chat. Lihat [Deployment](docs/DEPLOY.md).

## Riwayat perubahan 3.1

- Antrean cepat dan lambat terpisah (4 worker masing-masing), adil per chat, maksimum 250 pesan menunggu. AI/unduhan tidak memakai worker command ringan.
- Hasil command langsung dikirim; tidak ada lagi panggilan AI tambahan untuk komentar dekoratif. Hasil command disimpan sebagai konteks agar AI memahami pertanyaan lanjutan.
- AI memakai tool kalkulator, Wikipedia, katalog command, serta fitur baca saja yang tersedia. Command yang mengubah anggota, saldo, pengaturan, mengirim media, atau melakukan tindakan lain tetap diminta sebagai command eksplisit; izin admin tetap diperiksa.
- Wikipedia mencari judul terdekat, mengambil ringkasan, menyertakan sumber, dan memakai cache 30 menit. Mendukung Indonesia/Inggris.
- Kalkulator mendukung +, -, ×/x/*, ÷/bagi, pangkat ^/**, tanda kurung, persen, angka desimal berkoma, sqrt, abs, log/log10, sin/cos/tan (radian). Tidak menjalankan kode Python dari chat.
- Game `.jawab`/`.nyerah`, tebak bendera, pembacaan KBBI, setdesc, revoke link, audio-to-MP3, switch entertainment/feature pack, batas download, dan strike limit diperbaiki.
- Dashboard: AI playground, timeout/mode grup, jeda pengiriman, diagnostik, metrik durasi/error, ekspor-impor pengaturan tanpa rahasia, status native/provider, serta edit nama/deskripsi grup.
- Docker kini menyertakan `legacy/` yang dibutuhkan runtime; sebelumnya direktori itu dikecualikan oleh `.dockerignore`.

## Penggunaan

```text
.calc (12 + 8) × 3 / 2
.calc 2^8
.calc 15% * 200000
.calc sqrt(81)
hitung 120 dibagi 4
.wiki fotosintesis
.wiki en|photosynthesis
cari wikipedia tentang tata surya
```

Setelah `.wiki`, kirim misalnya “Jelaskan hasil tadi dengan bahasa sederhana”. Aktifkan **Ingat hasil command** agar konteks tersedia.

Untuk chat AI bebas: isi Base URL, Model, dan API key di dashboard. **AI tools** mengaktifkan function calling jika provider mendukungnya. Jika endpoint menolak schema tools (HTTP 400/422), bot mencoba chat tanpa tools satu kali; command `.calc`/`.wiki` dan pola `hitung ...` / `wiki ...` tetap berfungsi. Alias `.gemini`, `.openai`, dan alias AI lainnya menggunakan **model yang dikonfigurasi**, bukan otomatis beralih provider.

## Instalasi / upgrade

Baca **docs/UPGRADE.md** untuk pengguna VPS/systemd. Pertahankan `.env`, `ENCRYPTION_KEY`, dan seluruh `data/`. ZIP tidak memuat akun, API key, atau sesi WhatsApp.

Instalasi baru (Python 3.12, FFmpeg, libmagic):

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python scripts/setup.py
.venv/bin/python main.py
```

Docker: lihat docs/DEPLOY.md, termasuk hak baca `.env` untuk UID 10001.

## Pengaturan respons

Instalasi baru memakai cooldown input 0, jeda kirim global 0,3 detik dan per chat 0,7 detik, timeout AI 25 detik. Konfigurasi lama tetap dipertahankan: ubah **Features → Cooldown** menjadi 0 jika masih memakai nilai 2 dari versi sebelumnya. Jeda pengiriman bukan jaminan terhadap pembatasan WhatsApp.

Tidak ada jaminan delay nol: jaringan, API model, ukuran media, izin WhatsApp, dan kapasitas VPS tetap memengaruhi waktu respons. Pesan baru ditolak saat antrean penuh dan dicatat pada `Dropped`; tidak ada replay setelah proses crash.

## Batas fitur yang dijelaskan dengan jujur

- `Provider` pada katalog berarti belum ada integrasi native untuk fitur itu (misalnya generator gambar/video tertentu). Bot memberi penjelasan, bukan mengaku sudah membuat file.
- Dataset KBBI bawaan hanya daftar kata, **bukan definisi kamus**. `.kbbi` mengonfirmasi kata yang tersedia tanpa membuat definisi palsu.
- Downloader native menerima HTTPS YouTube/TikTok/Instagram. Alias platform lain tetap dikenali tetapi URL di luar daftar ini ditolak.
- Aturan moderasi/welcome dan mode AI berlaku global, bukan pengaturan terpisah per grup.
- Mode grup “Hanya chat menyebut Daffo” mendeteksi kata **Daffo** di teks; bukan deteksi mention JID WhatsApp.
- AI history ada di RAM: TTL satu jam, 700 sesi, jumlah turn dan karakter dibatasi. Restart proses menghapus history.

Lihat **docs/VALIDATION_REPORT.md** untuk hasil pengujian dan batas validasi.
