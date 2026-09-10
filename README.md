# STT Local — Dua Headset

Prototipe interkom lokal untuk dua headset USB melalui satu laptop, dengan transkripsi Bahasa Indonesia per pembicara.

## Yang sudah tersedia

- Deteksi perangkat audio Windows.
- Routing audio dua arah: mic A ke speaker B, serta mic B ke speaker A.
- VAD untuk memisahkan ucapan dari hening.
- Live STT berlabel pembicara A/B menggunakan `faster-whisper` model `small` pada CPU `int8`.
- Frontend lokal dengan pemilihan perangkat, status sesi, transkrip live, dan unduh TXT.
- Penyimpanan hasil sesi dalam `storage/sessions/` sebagai JSON dan TXT.

## Menjalankan

1. Hubungkan dua headset USB berkabel.
2. Jalankan PowerShell dari folder proyek:

   ```powershell
   .\scripts\run.ps1
   ```

3. Buka [http://127.0.0.1:8000](http://127.0.0.1:8000).
4. Pilih Mic/Speaker untuk pengguna A dan B. Kedua mic harus berbeda, begitu pula kedua speaker.
5. Gunakan **Uji mic A** atau **Uji mic B** terlebih dahulu. Indikator level bergerak ketika mic yang dipilih menangkap suara. Uji ini tidak meneruskan suara ke headset sehingga aman dari echo.
6. Pilih **Mulai sesi**. Model Whisper `small` tersedia lokal di folder `models/faster-whisper/`.

Untuk melihat daftar perangkat dari terminal:

```powershell
.\scripts\list-devices.ps1
```

## Catatan penggunaan

- Gunakan headset, bukan speaker laptop, agar tidak terjadi feedback/echo.
- Model disimpan dalam `models/` dan hasil sesi dalam `storage/`; keduanya sengaja tidak dilacak Git.
- Aplikasi mendengarkan hanya pada `127.0.0.1`, sehingga tidak terbuka untuk jaringan lokal.
- Jalur suara tidak menunggu proses STT. Teks normalnya muncul setelah sebuah frasa selesai, bukan setiap kata.
- Bahasa dideteksi otomatis agar ucapan Indonesia, Inggris, atau campuran dapat ditulis apa adanya.

## Batas MVP

Perekaman audio, SRT, terjemahan, akun pengguna, database, dan backend Go belum dibuat. Fase ini memvalidasi audio routing dan kualitas STT lebih dahulu.

## Pemeriksaan teknis

Jalankan dari folder `audio-stt`:

```powershell
python -m unittest discover -s tests -v
```

## Satu skrip untuk cek, setup, dan menjalankan

Jalankan dari folder proyek:

```powershell
# Cek Python, dependensi, Whisper small/medium, Ollama, dan Qwen 3B
.\scripts\stt-local.ps1

# Pasang dependensi dan model Whisper small bila belum ada
.\scripts\stt-local.ps1 -Action setup

# Tambahkan model Whisper medium
.\scripts\stt-local.ps1 -Action setup -WithMedium

# Tambahkan editor bahasa Qwen 3B melalui Ollama
.\scripts\stt-local.ps1 -Action setup -WithLlm

# Jalankan aplikasi
.\scripts\stt-local.ps1 -Action run
```

Untuk penggunaan paling sederhana, jalankan satu perintah ini saja. Ia memasang kebutuhan yang belum ada, memastikan Whisper `small`, `medium`, dan Qwen 3B tersedia, lalu membuka aplikasi:

```powershell
.\scripts\start.ps1
```

`start.ps1` otomatis memanggil `setup.ps1`. Jalankan `setup.ps1` sendiri bila hanya ingin menyiapkan seluruh kebutuhan tanpa membuka aplikasi.
