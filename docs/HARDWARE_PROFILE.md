# Profil perangkat

## Standard, perangkat saat ini

- CPU: Intel i7-1165G7, 4 core / 8 thread
- RAM: 16 GB
- GPU: Intel Iris Xe
- STT: `faster-whisper small`, CPU `int8`
- Bahasa: otomatis, dengan pilihan Indonesia, Sunda, atau Inggris saat uji mic
- LLM editor: nonaktif

Profil ini memprioritaskan audio interkom dan transkrip live. Hasil mentah Whisper adalah sumber utama agar sistem tidak mengubah makna ucapan.

## Upgrade nanti

| Kondisi perangkat | STT | Editor bahasa |
|---|---|---|
| RAM 32 GB atau GPU NVIDIA | `medium` | Qwen 3B, 4-bit |
| GPU NVIDIA kuat | `large-v3` | Qwen 7B, 4-bit |

Aktifkan upgrade melalui `.env` tanpa mengubah kontrak event transkrip:

```text
STT_PROFILE=high_accuracy
STT_MODEL=medium
STT_COMPUTE_TYPE=int8_float16
LLM_ENABLED=true
LLM_MODEL=qwen2.5:3b-instruct-q4_K_M
```

LLM hanya menerima hasil final dan menyimpan dua versi: `raw_text` dan `clean_text`. Ia tidak dipakai pada jalur audio atau partial transcript.
