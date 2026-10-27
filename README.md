# STT at Home

Self-hosted speech-to-text for local network use. Record audio from any device on your LAN, get a transcription back instantly.

Built with [whisper.cpp](https://github.com/ggml-org/whisper.cpp) for transcription, a FastAPI backend, and a minimal browser UI served over HTTPS — so microphone access works on mobile without any app install.

All audio stays on your own hardware. Nothing leaves your network. That is the whole point: it replaces the cloud dictation in AI chat apps for journaling (Obsidian), without handing a diary to an AI company.

---

## Architecture

```
browser (PWA)  ──HTTPS:8443──▶  nginx-fe  ──/api/──▶  python-be  ──▶  whisper-api
                                (static UI,            (FastAPI,        (whisper.cpp
                                 self-signed cert)      ffmpeg → wav)    whisper-server)
```

| Service | Source | Role |
|---|---|---|
| `nginx-fe` | `frontend/` | Serves `index.html` + PWA assets, terminates TLS, proxies `/api/` |
| `python-be` | `backend/main.py` | Converts any upload to 16 kHz mono WAV with ffmpeg, forwards to whisper |
| `whisper-api` | `ghcr.io/ggerganov/whisper.cpp:main` | Runs `whisper-server` with the model from `./models` |

The TLS cert is self-signed and generated on first start by `frontend/entrypoint.sh` (stored in the `ssl-certs` volume). Browsers will warn once; accept it so the mic works.

## Model and hardware

- **Model:** `ggml-large-v3-turbo.bin` — OpenAI Whisper large-v3-turbo, the newest open-weight Whisper (as of Oct 2026). Newer OpenAI speech models (`gpt-4o-transcribe`, `gpt-transcribe`, `gpt-live-transcribe`) are API-only and therefore out of scope.
- **CPU only.** The host doesn't have enough VRAM, so whisper.cpp runs on CPU with `-t 6` (6 threads). Tune `-t` in `docker-compose.yml` to the cores given to the CT; more threads than physical cores slows it down.
- **Languages:** Dutch (default) and English, picked with the toggle in the UI. The language is forced rather than auto-detected, which is more reliable for short clips.
- **Faster variant (optional):** a quantized `ggml-large-v3-turbo-q8_0.bin` (or `-q5_0`) is noticeably faster on CPU with nearly the same accuracy. See *Whisper model update* in [docs/update_guide.md](docs/update_guide.md).

### Considered alternatives

Checked Oct 2026, not adopted (Whisper's Dutch + English quality is the reason to stay):

- **NVIDIA Parakeet TDT 0.6B v3**: 25 European languages including Dutch, several times faster than Whisper on CPU, doesn't invent text during silences. Needs a test on real Dutch journal audio before considering it.
- **Mistral Voxtral Mini 4B Realtime**: true word-by-word streaming, Dutch supported, Apache 2.0. Built for a GPU; CPU inference via `voxtral.cpp`/llama.cpp GGUF is experimental.

## Setup

On the host (a Proxmox LXC CT with Docker):

```bash
git clone <this repo> stt-at-home && cd stt-at-home
mkdir -p models
curl -L -o models/ggml-large-v3-turbo.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
docker compose up --build -d
```

Open `https://<CT-IP>:8443`, accept the certificate, and add the page to your home screen to install it as a PWA.

## Using it

Tap the button to record, tap again to stop. The text appears in the result card, which has a copy button, and is added to the history (the last 50 transcripts, stored in the browser's `localStorage`).

If a transcription fails, the recording is kept in IndexedDB and a retry button shows up, even after the page is reloaded.

## Maintenance

See [docs/update_guide.md](docs/update_guide.md).
