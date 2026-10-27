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

Same `python:3.11-slim` base in **`parakeet/Dockerfile`**. Keep both in sync.

---

## 2. Python packages

No lockfile. Packages are pinned in `backend/requirements.txt` and `parakeet/requirements.txt`:

```
fastapi==0.x.x
uvicorn[standard]==0.x.x
python-multipart==0.x.x
httpx==0.x.x
```

Check for updates and bump versions manually:

```bash
pip index versions fastapi uvicorn python-multipart httpx onnx-asr
```

`onnx-asr` (in `parakeet/requirements.txt`) runs the speech model. On a bump, check its [releases](https://github.com/istupakov/onnx-asr/releases) for changes to `load_model` / `load_vad` / `recognize`, and listen-test Dutch transcription afterwards.

Or check [pypi.org](https://pypi.org) for each package. For major bumps on FastAPI or uvicorn, skim the changelog for breaking changes first.

---

## 3. Rebuild and test

From the project root on the CT:

```bash
docker-compose up --build -d
```

Verify all containers are running:

```bash
docker-compose ps
```

Open the app in a browser (`https://<CT-IP>:8443`), record a short audio clip, and confirm a transcription comes back. After a rebuild of `parakeet-api`, the model stays cached in the `hf-cache` volume, so no re-download. Check logs if anything looks off:

```bash
docker-compose logs -f
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
2. `docker-compose up --build -d`
3. Test transcription end-to-end

**Parakeet model update** (newer Parakeet or another onnx-asr model):

1. Check onnx-asr's [supported model names](https://istupakov.github.io/onnx-asr/usage/#supported-model-names) for the new name, and that it supports Dutch.
2. Change the name in `load_model(...)` in `parakeet/main.py`.
3. `docker-compose up --build -d parakeet-api`. The new model downloads on first start.
4. Test transcription in both Dutch and English.

Old models stay in the `hf-cache` volume. To clear it, run `docker-compose down` and then `docker volume rm <project>_hf-cache` (find the name with `docker volume ls`). The next start re-downloads.

**Switch back to Whisper**: see README → _Engine history and alternatives_.
