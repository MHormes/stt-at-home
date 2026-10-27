# STT at Home

Self-hosted speech-to-text for local network use. Record audio from any device on your LAN, get a transcription back within seconds.

Built with [NVIDIA Parakeet TDT 0.6B v3](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3) (via [onnx-asr](https://github.com/istupakov/onnx-asr)) for transcription, a FastAPI backend, and a minimal browser UI served over HTTPS — so microphone access works on mobile without any app install.

All audio stays on your own hardware. Nothing leaves your network. That is the whole point: it replaces the cloud dictation in AI chat apps for journaling (Obsidian), without handing a diary to an AI company.

---

## Architecture

```
browser (PWA)  ──HTTPS:8443──▶  nginx-fe  ──/api/──▶  python-be  ──▶  parakeet-api
                                (static UI,            (FastAPI,        (onnx-asr,
                                 self-signed cert)      ffmpeg → wav)    Parakeet + silero VAD)
```

| Service        | Source            | Role                                                                     |
| -------------- | ----------------- | ------------------------------------------------------------------------ |
| `nginx-fe`     | `frontend/`       | Serves `index.html` + PWA assets, terminates TLS, proxies `/api/`        |
| `python-be`    | `backend/main.py` | Converts any upload to 16 kHz mono WAV with ffmpeg, forwards to Parakeet |
| `parakeet-api` | `parakeet/`       | Runs Parakeet TDT 0.6B v3 (int8 ONNX) on CPU                             |

The TLS cert is self-signed and generated on first start by `frontend/entrypoint.sh` (stored in the `ssl-certs` volume). Browsers will warn once; accept it so the mic works.

## Model and hardware

- **Model:** NVIDIA Parakeet TDT 0.6B v3, int8-quantized ONNX (`nemo-parakeet-tdt-0.6b-v3` in onnx-asr). License CC-BY-4.0. On first start, `parakeet-api` downloads it (~640 MB) plus the silero VAD from Hugging Face into the `hf-cache` volume. That is a model download only; audio never leaves the CT.
- **Languages:** 25 European languages including Dutch and English. Language is **auto-detected**; there is no language setting.
- **Long audio:** Parakeet handles ~20–30 s at once, so the silero VAD splits recordings at pauses and the segment texts are joined.
- **Hardware:** Proxmox LXC CT with 6 cores of an Intel i7-10710U (15 W laptop chip). No GPU.
- **Speed (measured Oct 2026):** 32.2 s of audio in 3.8 s with Parakeet (~8.5× real time), against 57.9 s with Whisper large-v3-turbo.

### Engine history and alternatives

- **Whisper large-v3-turbo (whisper.cpp), until Oct 2026.** Very good Dutch and English, but on this CPU each 30 s window cost ~28 s, the same for the f16 and q5_0 models (the build already used AVX2/FMA). Since Oct 2026 Parakeet is on trial as the main engine. The Whisper models are still in `./models` on the CT. To switch back, restore the Whisper-only version (commit `e3d5aef`): `git checkout e3d5aef -- docker-compose.yml backend/main.py frontend/index.html`, then `docker-compose up --build -d --remove-orphans`. Possible Whisper speedups that weren't tried: the Intel UHD 620 iGPU via OpenVINO, or `--audio-ctx` for short clips.
- **Transcribe-while-talking with Whisper (tried and reverted, Oct 2026):** with Whisper's fixed ~28 s cost per window, segments queued up faster than they were processed and the total wait got longer. Now back on trial with Parakeet (see _Using it_).
- **Mistral Voxtral Mini 4B Realtime:** true word-by-word streaming, Dutch supported, Apache 2.0. Built for a GPU; CPU inference via `voxtral.cpp`/llama.cpp GGUF is experimental.
- OpenAI's newer speech models (`gpt-4o-transcribe`, `gpt-transcribe`, `gpt-live-transcribe`) are API-only and therefore out of scope.

## Setup

On the host (a Proxmox LXC CT with Docker and docker-compose v1):

```bash
git clone <this repo> stt-at-home && cd stt-at-home
docker-compose up --build -d
docker-compose logs -f parakeet-api   # first start: wait for the model download and "Uvicorn running"
```

Open `https://<CT-IP>:8443`, accept the certificate, and add the page to your home screen to install it as a PWA.

## Using it

Tap the button to record, tap again to stop. The text appears in the result card, which has a copy button, and is added to the history (the last 50 transcripts, stored in the browser's `localStorage`).

If a transcription fails, the recording is kept in IndexedDB and a retry button shows up, even after the page is reloaded.

`python-be` logs `transcribed Xs audio in Ys` for every request.

### Transcribe-while-talking

Parakeet can't stream, so the frontend fakes it: it listens to the mic level and cuts the recording at natural pauses into segments of roughly 5–20 s. Each segment goes to `/api/transcribe` while you keep talking, and text appears in the result card as segments finish. At stop, only the last segment still needs processing.

- Segments with no detected speech are skipped.
- If any segment fails, the full recording (captured in parallel with `MediaRecorder`) is transcribed in one go instead, with the usual retry button.
- Browsers without AudioWorklet fall back to the plain record → upload → transcribe flow.
- Tuning knobs are at the top of the script in `frontend/index.html`: `SEG_MIN_SEC`, `SEG_MAX_SEC`, `SILENCE_CUT_SEC`. Shorter segments make text appear sooner, but Parakeet sees less context per piece, which can cost accuracy at the cut points.

## Maintenance

See [docs/update_guide.md](docs/update_guide.md).
