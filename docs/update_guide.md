# STT at Home — Update Guide (every 2 months)

Run after the OS update for CT 104 in `update-guide-nuc.md`. Take a CT snapshot first; it is deleted in step 5.

---

## 1. Docker base image bumps

Check each base image for patch/minor bumps and update in place.

**`backend/Dockerfile`** and **`parakeet/Dockerfile`** — Python base image (keep both in sync):

```dockerfile
FROM python:3.11-slim
```

Check [hub.docker.com/\_/python](https://hub.docker.com/_/python). Patch bumps are pulled automatically by `--pull` in step 4. A minor bump (e.g. 3.11 → 3.12) is an occasional task, see below.

**`frontend/Dockerfile`** — nginx base image:

```dockerfile
FROM nginx:1.25-alpine
```

Check [hub.docker.com/\_/nginx](https://hub.docker.com/_/nginx) for a newer `x.x-alpine` (stable line). Bump the tag if there is one.

---

## 2. Check Python packages

No lockfile. Packages are pinned with `==` in `backend/requirements.txt` and `parakeet/requirements.txt`.

Get the latest version of each package (`pip index versions` takes one package at a time):

```powershell
# PowerShell (Windows)
foreach ($p in "fastapi","uvicorn","python-multipart","httpx","onnx-asr") { pip index versions $p 2>$null | Select-Object -First 1 }
```

```bash
# bash
for p in fastapi uvicorn python-multipart httpx onnx-asr; do pip index versions "$p" 2>/dev/null | head -1; done
```

Example output:

```
fastapi (0.121.0)
uvicorn (0.38.0)
...
```

Ignore the `pip index is experimental` warning and the `new release of pip` notice.

Package notes:

- **fastapi / uvicorn**: 0.x packages, so minor bumps can break things. Skim the [FastAPI release notes](https://fastapi.tiangolo.com/release-notes/) and [uvicorn changelog](https://www.uvicorn.org/release-notes/).
- **uvicorn**: in requirements it's `uvicorn[standard]==x.y.z`. Only change the version and keep `[standard]`.
- **onnx-asr** (`parakeet/requirements.txt`, runs the speech model): check its [releases](https://github.com/istupakov/onnx-asr/releases) for changes to `load_model` / `load_vad` / `recognize`. Test Dutch transcription after a bump.
- If a package is in both files, use the same version in both.

---

## 3. Commit the bumps

Commit the Dockerfile and requirements changes, then pull them onto the CT (or copy them over the way you normally deploy).

---

## 4. Rebuild and test

From the project root on the CT:

```bash
docker-compose build --pull
docker-compose up -d
docker-compose ps
```

All containers should be `Up`. If one keeps restarting, check its logs with `docker-compose logs <service>`. Usually the cause is a package bump: revert that one pin and rebuild.

Open the app (`https://<CT-IP>:8443`), record a short clip in Dutch and one in English, and confirm both come back transcribed correctly. The model stays cached in the `hf-cache` volume, so there is no re-download. If something looks off:

```bash
docker-compose logs -f
```

Clean up old images afterwards:

```bash
docker image prune -f
```

---

## 5. Delete CT snapshot

Once the rebuild and transcription test both work, delete the snapshot in the Proxmox UI, or on the host:

```bash
pct delsnapshot 104 <snapshot-name>
```

If something is broken and you can't fix it, roll back instead: `pct rollback 104 <snapshot-name>`.

---

## Occasional tasks

**Python minor upgrade** (e.g. 3.11 → 3.12):

1. Update `FROM python:x.x-slim` in **both** `backend/Dockerfile` and `parakeet/Dockerfile`.
2. Check that onnx-asr and onnxruntime support the new Python version on PyPI.
3. `docker-compose build --pull && docker-compose up -d`
4. Test transcription end-to-end and look in the logs for deprecation warnings.

**Parakeet model update** (newer Parakeet or another onnx-asr model):

1. Check onnx-asr's [supported model names](https://istupakov.github.io/onnx-asr/usage/#supported-model-names) for the new name, and that it supports Dutch.
2. Change the name in `load_model(...)` in `parakeet/main.py`.
3. `docker-compose up --build -d parakeet-api`. The new model downloads on first start.
4. Test transcription in both Dutch and English.

Old models stay in the `hf-cache` volume. To clear it, run `docker-compose down` and then `docker volume rm <project>_hf-cache` (find the name with `docker volume ls`). The next start re-downloads.
