# Arsitektur 3.1

`main.py` memuat `.env` lalu menjalankan FastAPI satu worker. Lifespan membuka control.db dan bot. `legacy.db` menyimpan game economy/strike; sesi WhatsApp menggunakan whatsapp-session.db.

## Penjadwalan

`Scheduler` membagi pesan ke lane cepat dan lambat, empat worker per lane. Masing-masing lane menjaga FIFO per chat dan satu pekerjaan aktif per chat. Chat sibuk tidak memenuhi worker dengan pekerjaan yang hanya menunggu chat yang sama. Total pesan menunggu maksimal 250; overflow dicatat sebagai dropped. Dua lane dapat berjalan bersamaan pada chat sama sehingga `.ping` tidak harus menunggu percakapan AI selesai. Urutan balasan lintas lane tidak dijamin; urutan dalam satu lane dipertahankan.

Legacy handler berjalan pada executor khusus empat thread. Pemanggilan async Neonize dijembatani ke event loop. Pekerjaan yang dibatalkan tidak boleh mengirim pesan setelah dibatalkan. Thread Python tidak bisa dihentikan paksa; operasi jaringan dan FFmpeg dibatasi timeout dan slot tetap ditahan sampai thread selesai. Saat shutdown executor ditunggu sebelum database ditutup.

`SendGate` tidak menahan kunci global saat menunggu jeda sebuah chat. Default global 0,3 detik, per chat 0,7 detik, dapat diubah. Ini pacing lokal, bukan jaminan batas WhatsApp.

## AI

HTTPX persistent client, maksimum empat request AI bersamaan, timeout konfigurabel, tidak retry timeout/429 secara otomatis. Tiga kegagalan provider membuka circuit 60 detik. Perubahan model/key/endpoint mereset kemampuan tools dan circuit. Maksimum dua putaran tools (tiga tool per putaran), lalu jawaban final. Batas waktu seluruh proses AI adalah timeout konfigurasi + 20 detik.

Tools: kalkulator, Wikipedia, katalog command dan bot_command baca saja. Aksi lain dikembalikan sebagai petunjuk command eksplisit. Tool data ditempatkan sebagai hasil tool, bukan system instruction. Sumber Wikipedia ditambahkan jika model lupa mencantumkannya. Bila ringkasan AI gagal setelah tool berhasil, hasil tool yang tersedia dikirim langsung.

Panggilan tambahan untuk memoles balasan command dihapus. Toggle `ai_command_assist` berarti menyimpan hasil command untuk konteks AI. Empat hasil terakhir per sesi disimpan sampai 30 menit. History percakapan TTL satu jam, maksimum 700 sesi, dibatasi turns dan total karakter. Reset memori tidak diisi kembali oleh request lama yang masih berjalan.

## Web

Argon2 login, sesi maksimal delapan jam, CSRF + Origin untuk perubahan, JSON body maksimal 32 KiB, lima percobaan login per lima menit. API key terenkripsi Fernet dan tidak dikembalikan melalui API konfigurasi/ekspor. SSE status dua detik dan polling fallback ketika SSE putus. Start/stop/restart diserialkan. AI playground tidak mengirim WhatsApp.

Konfigurasi feature pack diperiksa tiap command, sehingga switch bekerja tanpa restart. Moderasi/welcome/AI mode bersifat global. Strike limit benar-benar digunakan untuk penegakan moderasi, dengan bot wajib memiliki hak admin.

## Sumber implementasi API

- Neonize 0.5.2 yang dipasang untuk uji: signature `set_group_topic(jid, previous_id, new_id, topic)` dan `get_group_invite_link(jid, revoke=False)` diperiksa langsung.
- https://github.com/krypton-byte/neonize
- https://www.mediawiki.org/wiki/API:Search_and_discovery
- https://www.mediawiki.org/wiki/Extension:TextExtracts
