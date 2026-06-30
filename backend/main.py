import os
import httpx
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI()

WHISPER_URL = os.getenv("WHISPER_URL", "http://whisper-api:8080/inference")


@app.get("/api/health")
def health():
    return {"status": "ok", "whisper_url": WHISPER_URL}


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), language: str = "nl"):
    data = await audio.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio file")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(
                WHISPER_URL,
                files={"file": (audio.filename or "recording.webm", data, audio.content_type or "audio/webm")},
                data={"language": language},
            )
            resp.raise_for_status()
        except httpx.HTTPError as e:
            raise HTTPException(status_code=502, detail=f"Whisper error: {e}")

    result = resp.json()
    return {
        "text": result.get("text", "").strip(),
        "language": result.get("language", "nl"),
    }
