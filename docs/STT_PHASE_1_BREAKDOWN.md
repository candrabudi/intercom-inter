# STT Local — Fase 1: Audio Interkom dan Live Transkripsi

## Tujuan

Membangun prototipe lokal untuk dua pengguna yang memakai dua headset melalui satu laptop. Sistem meneruskan suara dua arah dan menampilkan transkrip Bahasa Indonesia secara langsung, dengan pembicara A dan B selalu dipisahkan.

Seluruh audio, model, dan transkrip tetap berada di laptop. Aplikasi hanya dibuka melalui `localhost`.

## Ruang lingkup

### Termasuk

- Memilih dua headset sebagai perangkat input dan output terpisah.
- Interkom dua arah: mic A ke headset B, serta mic B ke headset A.
- Live STT per mic dengan `faster-whisper` model `small` pada CPU `int8`.
- Deteksi bagian ucapan (VAD) supaya audio hening tidak ditranskripsikan.
- Frontend web lokal sederhana untuk memulai dan menghentikan sesi, memilih perangkat, melihat status, serta membaca transkrip.
- Penyimpanan transkrip sesi lokal dalam JSON dan TXT.

### Belum termasuk

- User, login, role, database, dan API Go.
- Terjemahan bahasa.
- Speaker diarization; pembicara sudah diketahui dari mic/headset A atau B.
- Dukungan beberapa laptop atau komunikasi jaringan.
- Perekaman audio permanen. Ini dapat ditambahkan setelah alur dasar stabil.

## Perangkat yang diperlukan

- Satu laptop Windows dengan Python 3.11.
- Dua headset USB berkabel, masing-masing memiliki microphone dan speaker.
- Opsional: USB hub berkualitas atau USB audio adapter jika port USB terbatas.

> Hindari memakai dua headset Bluetooth pada MVP. Input mic ganda dan latensi profil Bluetooth di Windows lebih sulit dibuat stabil.

FFmpeg belum diperlukan pada fase live-STT ini. Ia baru diperlukan bila fase berikutnya menambah upload dan konversi file audio/video.

## Arsitektur

```text
Mic headset A ─┬─> Audio router ────────────────> Speaker headset B
               └─> VAD A -> antrean STT A -> transkrip A ─┐
                                                          │
Mic headset B ─┬─> Audio router ────────────────> Speaker headset A
               └─> VAD B -> antrean STT B -> transkrip B ─┼─> WebSocket -> UI lokal
                                                          │
                                              session store ┘
```

Jalur audio dan STT harus dipisahkan. Router audio meneruskan PCM sesegera mungkin untuk menjaga percakapan nyaman; STT menerima salinan audio dalam potongan pendek sehingga keterlambatan teks tidak menahan suara.

## Struktur folder

```text
STT-LOCAL/
├── docs/
│   └── STT_PHASE_1_BREAKDOWN.md
├── audio-stt/
│   ├── app/
│   │   ├── main.py              # FastAPI, lifecycle aplikasi
│   │   ├── config.py            # path, model, dan parameter audio
│   │   ├── devices.py           # inventaris dan validasi headset
│   │   ├── router.py            # mic A -> speaker B, mic B -> speaker A
│   │   ├── vad.py               # pengelolaan potongan ucapan
│   │   ├── stt.py               # load dan panggil faster-whisper
│   │   ├── session.py           # state sesi dan urutan event
│   │   ├── store.py             # simpan JSON/TXT lokal
│   │   └── websocket.py         # event live ke browser
│   ├── requirements.txt
│   └── tests/
│       ├── test_devices.py
│       ├── test_router.py
│       └── test_stt.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── models/
│   └── faster-whisper/
│       └── small/               # diunduh otomatis saat pertama kali dijalankan
├── storage/
│   └── sessions/
├── scripts/
│   ├── run.ps1
│   └── list-devices.ps1
├── .env.example
└── .gitignore
```

Folder `models/` dan `storage/` tidak dimasukkan ke Git.

## Konfigurasi awal yang disarankan

| Bagian | Nilai awal |
|---|---|
| Model | `small` |
| Engine | `faster-whisper` |
| Perangkat komputasi | CPU |
| Presisi | `int8` |
| Bahasa | Indonesia (`id`) |
| Format audio internal | mono PCM, 16 kHz untuk STT |
| Mode routing audio | PCM real-time, sample rate mengikuti perangkat jika diperlukan |
| Jeda teks target | 1–3 detik setelah frasa selesai |

## Event transkrip

Setiap hasil final dikirim ke UI dan disimpan dengan bentuk seperti berikut:

```json
{
  "type": "transcript.final",
  "session_id": "ses_20260910_001",
  "speaker": "A",
  "text": "Selamat pagi, apakah suara saya terdengar?",
  "started_at_ms": 12800,
  "ended_at_ms": 15700,
  "is_final": true
}
```

## Tahapan implementasi

### 1. Fondasi aplikasi

- Buat virtual environment Python, dependensi, konfigurasi path, dan skrip run.
- Verifikasi FFmpeg serta perangkat audio dapat dibaca dari Windows.
- Kriteria selesai: perintah pemeriksaan perangkat menampilkan input dan output yang tersedia.

### 2. Pemilihan perangkat dan interkom

- UI atau konfigurasi memilih mic/speaker A dan B.
- Tangkap audio dari kedua mic secara paralel.
- Rute mic A ke speaker B dan mic B ke speaker A.
- Kriteria selesai: dua pengguna dapat berbicara dua arah tanpa echo atau putus suara yang mengganggu.

### 3. Buffer audio dan VAD

- Salin audio dari setiap mic ke buffer STT masing-masing.
- Gunakan VAD untuk menentukan awal dan akhir frasa.
- Tambahkan batas durasi agar ucapan panjang tetap diproses bertahap.
- Kriteria selesai: hening tidak menghasilkan transkrip dan frasa tidak sering terpotong.

### 4. Worker STT

- Unduh dan muat model `small` sekali saat aplikasi dimulai.
- Jalankan worker terpisah untuk antrean A dan B agar satu pihak tidak menghambat pihak lain.
- Tambahkan timestamp dan label pembicara.
- Kriteria selesai: dua jalur percakapan menghasilkan teks Indonesia yang benar dan berurutan.

### 5. Frontend sederhana

- Buat halaman pemilihan perangkat dan kontrol sesi.
- Tampilkan indikator koneksi, status mic, serta dua kolom transkrip.
- Kirim event dengan WebSocket dan tampilkan hasil final secara langsung.
- Kriteria selesai: sesi dapat dikendalikan dan teks muncul tanpa me-refresh halaman.

### 6. Penyimpanan dan ekspor

- Simpan metadata dan event ke `storage/sessions/<session-id>.json`.
- Susun event berdasarkan waktu dan ekspor TXT.
- Kriteria selesai: hasil sesi tetap tersedia setelah aplikasi dihentikan.

### 7. Uji lapangan

- Uji percakapan nyata 15–30 menit menggunakan dua headset.
- Ukur latensi komunikasi, keterlambatan teks, beban CPU, dan kesalahan transkripsi.
- Catat istilah yang perlu ditambahkan sebagai prompt/kamus.
- Kriteria selesai: aplikasi stabil untuk satu sesi uji tanpa crash dan tanpa audio yang tercampur.

## Risiko teknis dan mitigasi

| Risiko | Mitigasi |
|---|---|
| Perangkat Windows berubah urutan | Simpan pilihan berdasarkan nama/id perangkat dan validasi sebelum sesi dimulai. |
| Echo atau feedback | Gunakan headset tertutup, bukan speaker laptop; jangan rute audio ke perangkat yang salah. |
| Teks terlambat | Jaga routing audio tetap terpisah; gunakan `small`, VAD, dan antrean STT per pembicara. |
| CPU penuh | Gunakan `int8`, batasi panjang potongan, dan hentikan aplikasi berat lain saat uji. |
| Kalimat terpotong | Tuning parameter VAD dan tambahkan sedikit audio sebelum/sesudah potongan. |

## Definisi selesai untuk MVP

MVP dianggap selesai ketika dua headset USB dapat saling berkomunikasi melalui laptop, masing-masing mic menghasilkan transkrip Indonesia berlabel A/B secara live, dan hasil sesi dapat disimpan sebagai TXT/JSON tanpa mengirim audio ke internet.
