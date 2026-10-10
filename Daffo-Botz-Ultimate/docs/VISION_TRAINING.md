# Vision & Studio Pelatihan — v3.2

## Model AI dan gambar

Di **Mesin AI**, isi Base URL HTTPS yang termasuk `AI_ALLOWED_HOSTS`, model, dan API key provider Anda. Di **Vision Lab**, model vision boleh dikosongkan untuk memakai model utama. Jika model utama tidak menerima gambar, pilih model multimodal milik provider yang sama. Kunci API tidak dipindahkan ke dataset pelatihan.

Vision mengirim pesan berisi teks dan `image_url` berupa data URL ke endpoint `/chat/completions`. Provider harus menerima schema OpenAI-compatible tersebut. Provider yang menolak gambar menampilkan error; bot tidak membuang gambar diam-diam untuk menghasilkan jawaban teks. Tidak ada jaminan dukungan vision hanya dari nama model `auto`.

Di WhatsApp:

```text
[kirim foto dengan caption] Apa isi gambar ini?
[kirim atau balas foto] .lihat Jelaskan produk ini
[balas foto] .ocr
```

Auto-reply mengikuti switch AI, private/group, dan mode mention. Command eksplisit bekerja tanpa auto-reply private/group, selama AI/key/vision aktif. Gambar tanpa caption dapat diproses di chat pribadi; grup mention memerlukan kata Daffo. Image biasa dan ephemeral didukung; media view-once tetap tidak diproses. Ukuran maksimal 5 MB, format JPEG/PNG/WebP, maksimal 20 megapiksel. Sebelum dikirim ke AI, gambar dikonversi ke JPEG maksimal 1600 piksel pada sisi terpanjang dan metadata dibuang.

Gambar diteruskan ke provider eksternal dan dapat memiliki biaya. Kebijakan retensi provider berlaku. Aplikasi tidak menambahkan gambar mentah ke history percakapan atau database. Jawaban hasil analisis dapat tersimpan di history RAM yang sudah ada. Deteksi objek/OCR memakai model vision dan mungkin salah; periksa teks penting secara manual.

## Ajari bot

1. Isi profil, tujuan, bahasa, prinsip, serta perilaku ketika belum tahu, lalu simpan draft.
2. Tambahkan dokumen faktual: FAQ, kebijakan, katalog, panduan. Maksimal 100 dokumen, masing-masing 12.000 karakter. File teks/Markdown dapat dimuat melalui form.
3. Tambahkan contoh pertanyaan/jawaban (maksimal 100). Contoh yang relevan membantu gaya respons.
4. Uji pertanyaan di ruang simulasi. Tanpa switch jawaban AI, hasilnya menunjukkan potongan dokumen yang berhasil ditemukan tanpa memerlukan API key.
5. Tambahkan kasus Quality checks. Frasa wajib dipisahkan koma. Retrieval mendukung sampai 30 kasus; uji AI sampai 10 kasus dan memakai kuota provider.
6. Beri label versi dan pilih **Terbitkan ke bot**. Versi aktif digunakan pada permintaan AI berikutnya, jika switch pengetahuan aktif.

Draft tidak memengaruhi pengetahuan bot sampai dipublikasikan. Studio menggunakan pencarian BM25 pada potongan teks dan contoh few-shot relevan; **tidak melatih bobot model, tidak memerlukan GPU, dan bukan pencarian embedding semantik**. Pencarian kata dapat melewatkan sinonim; tambahkan tag dan variasi pertanyaan. Skor retrieval bukan probabilitas kebenaran. Quality checks hanya memeriksa adanya frasa wajib, bukan kebenaran atau kualitas menyeluruh jawaban.

## Versi dan data

SQLite `data/control.db` menyimpan profil, dokumen, contoh, kasus uji, draft, versi aktif, dan 20 publikasi terakhir. Memulihkan versi mengubah versi aktif; draft tetap ada. Publikasi/rollback membersihkan memori AI agar konteks lama tidak terus memengaruhi jawaban. Menyimpan draft tidak menghapus memori live.

Setiap perubahan memakai nomor revisi. Jika ada edit dari sesi lain, API mengembalikan 409; muat ulang studio sebelum mengulang perubahan. Ekspor berisi draft saja. Impor mengganti draft setelah konfirmasi, tidak mengganti versi aktif, dan menolak field asing serta ID duplikat. Dataset tidak mengandung API key atau sesi WhatsApp, tetapi tetap berisi teks yang Anda tulis; periksa sebelum membagikannya.

Backup `.env` dan seluruh `data/` saat bot berhenti. Jangan mengganti `ENCRYPTION_KEY` yang sudah dipakai. Data studio tidak dienkripsi terpisah; database dilindungi permission lokal 600 seperti konfigurasi yang sudah ada.

## API

Semua endpoint memerlukan sesi admin. Mutasi dan pengujian POST/PUT/DELETE memerlukan Origin yang cocok dan CSRF token.

- `GET /api/training`: draft, revisi, versi, dan jumlah dokumen aktif.
- `PUT /api/training/profile`: `{revision, profile}`.
- `POST /api/training/documents|examples|evaluations`: `{revision, document|example|evaluation}`; ID yang sama memperbarui entri.
- `DELETE /api/training/{kind}/{id}`: `{revision}`.
- `POST /api/training/publish`: `{revision, label}`.
- `POST /api/training/rollback`: `{revision, version}`.
- `POST /api/training/preview`: `{prompt, mode: "draft"|"active", generate: false|true}`.
- `POST /api/training/evaluate`: `{mode, generate}`.
- `GET /api/training/export`, `POST /api/training/import`: impor `{revision, dataset}`.
- `POST /api/ai/test`: `{prompt, image_base64?}` untuk uji multimodal tanpa mengirim pesan WhatsApp.

## Hasil validasi

Tes memakai provider HTTP tiruan untuk memverifikasi payload gambar, pilihan model, knowledge injection, penolakan vision, dan privasi history. Alur pesan WhatsApp diuji dengan event protobuf dan client download tiruan. Browser nyata menguji draft, edit, publish, rollback, import/export, evaluasi, pratinjau gambar, tema dan mobile tanpa horizontal overflow.

Koneksi akun WhatsApp nyata dan kualitas jawaban model eksternal belum divalidasi karena tidak ada sesi/API key. Tes UI memverifikasi error yang jujur saat API key belum tersedia.
