import numpy as np
import onnx_asr
from fastapi import FastAPI, UploadFile, File, HTTPException

app = FastAPI()

# Parakeet only handles ~20-30s at once; the VAD splits longer audio at pauses
model = onnx_asr.load_model("nemo-parakeet-tdt-0.6b-v3", quantization="int8").with_vad(onnx_asr.load_vad("silero"))


def wav_to_float(data: bytes) -> np.ndarray:
    # 16 kHz mono s16 wav from the backend's ffmpeg. Piped wavs carry bogus chunk
    # sizes, so locate the data chunk and read everything after it.
    pos = data.find(b"data", 12)
    if pos < 0:
        raise HTTPException(status_code=400, detail="Not a wav file")
    pcm = data[pos + 8:]
    return np.frombuffer(pcm[: len(pcm) // 2 * 2], dtype="<i2").astype(np.float32) / 32768.0


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/transcribe")
def transcribe(file: UploadFile = File(...)):
    waveform = wav_to_float(file.file.read())
    text = " ".join(seg.text.strip() for seg in model.recognize(waveform, sample_rate=16000))
    return {"text": text}
