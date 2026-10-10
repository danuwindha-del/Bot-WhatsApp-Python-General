# 3.2 — Vision & Training Studio

- Dashboard didesain ulang dengan warna hijau alami, sidebar, tema terang/gelap, dan layout mobile.
- Input gambar multimodal pada AI yang dikonfigurasi; model vision opsional, sanitasi gambar, batas file/resolusi, dan error provider yang jelas.
- Auto-reply gambar WhatsApp, command `.lihat`, `.vision`, `.ocr`, quoted images, dan caption pesan ephemeral.
- Studio pengetahuan SQLite dengan retrieval BM25, profil, few-shot examples, draft/publikasi/rollback dan 20 versi.
- Simulasi draft/aktif, pengujian frasa wajib pada retrieval atau jawaban AI, serta dataset import/export.
- Konflik revisi mencegah overwrite perubahan dari sesi lain. Draft tidak menghapus memori percakapan; publikasi/rollback membersihkan konteks lama.
- Memperbaiki variabel `re` lokal yang menghalangi jalur AI pribadi.

# 3.1

- Antrean fair dua lane, pacing tanpa menahan lock saat sleep, metrik pemrosesan.
- Hilangkan round-trip AI tambahan pada setiap balasan command.
- AI tools dengan hasil nyata, konteks command, alias AI ke model terkonfigurasi, fallback provider tanpa tool support.
- Kalkulator AST terbatas, pencarian Wikipedia async + cache + sumber.
- Perbaiki bentrok sesi game, tebak bendera, KBBI, setdesc/revoke, audio message extraction.
- Terapkan switch entertainment/legacy, download limit dan strike limit.
- Dashboard playground, diagnostik, impor/ekspor, pengaturan pacing/AI, katalog status, edit grup, polling fallback.
- Sertakan legacy dalam build Docker, batasi executor, lindungi perintah owner dengan identitas PN.
- Pengujian regresi dan interaksi DOM/API, panduan upgrade mempertahankan sesi.
