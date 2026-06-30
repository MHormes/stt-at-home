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
image: ghcr.io/ggerganov/whisper.cpp:main-server
```

This always pulls the latest build on rebuild — no version pin to update.

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

Open the app in a browser (`https://<CT-IP>`), record a short audio clip, and confirm a transcription comes back. Check logs if anything looks off:

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

**Whisper model update** (new model released):

1. Download the new `.bin` to the `models/` directory on the CT
2. Update the `command` arg in `docker-compose.yml`:
   ```yaml
   command: ["-m", "/models/ggml-<new-model>.bin", "--port", "8080"]
   ```
3. `docker compose up --build -d` (or `docker compose restart whisper-api`)
4. Test transcription
