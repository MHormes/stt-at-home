import asyncio
import os
import re
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI()

WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper-api:8080/inference")


@app.get("/api/health")
def health():
    return {"status": "ok", "whisper_url": WHISPER_URL}


async def to_wav(data: bytes) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", "pipe:0", "-ar", "16000", "-ac", "1", "-f", "wav", "pipe:1",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    wav, err = await proc.communicate(input=data)
    if proc.returncode != 0:
        raise HTTPException(status_code=400, detail=f"Audio convert failed: {err.decode(errors='ignore')}")
    return wav


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = "nl"):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    wav_data = await to_wav(data)

    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            resp = await client.post(
                WHISPER_URL,
                files={"file": ("recording.wav", wav_data, "audio/wav")},
                data={"language": language},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Whisper error: {e}")

    result = resp.json()
    text = re.sub(r"\s+", " ", result.get("text", "")).strip()
    return {
        "text": text,
        "language": result.get("language", "nl"),
    }
