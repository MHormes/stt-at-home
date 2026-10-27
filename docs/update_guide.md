# STT at Home — Monthly Update Guide

Run after OS updates per the global `update_guide.md`.

---

## 1. Docker version bumps

Check each base image for patch/minor bumps and update in place.

**`backend/Dockerfile`** — Python base image:

```dockerfile
FROM python:3.11-slim
```

Check [hub.docker.com/_/python](https://hub.docker.com/_/python) for a newer `3.x-slim` patch or minor. Major version bump (e.g. 3.11 → 3.12): test thoroughly, check for deprecation warnings.

**`frontend/Dockerfile`** — nginx base image:

```dockerfile
FROM nginx:1.25-alpine
```

Check [hub.docker.com/_/nginx](https://hub.docker.com/_/nginx) for a newer `x.x-alpine` patch or minor.

**`docker-compose.yml`** — whisper.cpp image:

```yaml
image: ghcr.io/ggerganov/whisper.cpp:main
entrypoint: ["/app/build/bin/whisper-server"]
```

Unpinned `main` tag, so no version to bump, but `docker compose up --build` does **not** re-pull it. Pull explicitly:

```bash
docker compose pull whisper-api
```

Note: whisper.cpp moved from `ggerganov` to the `ggml-org` GitHub org. As of Oct 2026 both `ghcr.io/ggerganov/whisper.cpp:main` and `ghcr.io/ggml-org/whisper.cpp:main` exist but serve different images, so the old path is probably no longer updated. See *Switch whisper.cpp image to ggml-org* below.

---

## 2. Python packages

No lockfile — packages are pinned in `backend/requirements.txt`:

```
fastapi==0.x.x
uvicorn[standard]==0.x.x
python-multipart==0.x.x
httpx==0.x.x
```

Check for updates and bump versions manually:

```bash
pip index versions fastapi uvicorn python-multipart httpx
```

Or check [pypi.org](https://pypi.org) for each package. For major bumps on FastAPI or uvicorn, skim the changelog for breaking changes first.

---

## 3. Rebuild and test

From the project root on the CT:

```bash
docker compose up --build -d
```

Verify all containers are running:

```bash
docker compose ps
```

Open the app in a browser (`https://<CT-IP>:8443`), record a short audio clip, and confirm a transcription comes back. Check logs if anything looks off:

```bash
docker compose logs -f
```

---

## 4. Delete CT snapshot

After confirming the rebuild works: delete the Proxmox CT snapshot via the Proxmox UI or:

```bash
pct delsnapshot <CTID> <snapshot-name>
```

---

## Occasional tasks

**Python version upgrade** (e.g. 3.11 → 3.12):

1. Update `FROM python:x.x-slim` in `backend/Dockerfile`
2. `docker compose up --build -d`
3. Test transcription end-to-end

**Whisper model update** (new model released, or switching to a quantized variant):

Current model: `ggml-large-v3-turbo-q5_0.bin`, running on CPU. Ready-made files are at [huggingface.co/ggerganov/whisper.cpp](https://huggingface.co/ggerganov/whisper.cpp/tree/main). The `-q8_0` / `-q5_0` variants of a model are quantized: faster on CPU, with near-identical accuracy.

1. Download the new `.bin` to the `models/` directory on the CT:
   ```bash
   curl -L -o models/ggml-<new-model>.bin      https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-<new-model>.bin
   ```
2. Update the model path in the `command` arg in `docker-compose.yml`. Keep `--host 0.0.0.0` (without it the server only listens on localhost and `python-be` can't reach it) and `-t`:
   ```yaml
   command: ["-m", "/models/ggml-<new-model>.bin", "--host", "0.0.0.0", "--port", "8080", "-t", "6"]
   ```
3. `docker compose up -d whisper-api`
4. Test transcription in both Dutch and English

As of Oct 2026, large-v3-turbo is the newest open-weight Whisper. OpenAI's newer speech models are API-only. See README → *Considered alternatives* for non-Whisper options.

**Switch whisper.cpp image to ggml-org** (one-time):

1. In `docker-compose.yml`: `image: ghcr.io/ggml-org/whisper.cpp:main`
2. Check the server binary path is still `/app/build/bin/whisper-server`:
   ```bash
   docker run --rm --entrypoint ls ghcr.io/ggml-org/whisper.cpp:main /app/build/bin
   ```
3. `docker compose pull whisper-api && docker compose up -d whisper-api`
4. Test transcription

**Thread count** (`-t` in `docker-compose.yml`): match the number of physical cores assigned to the CT. More threads than that makes it slower.
