"""Run with: python -m uvicorn soniccraft.api.app:app --host 127.0.0.1 --port 8000."""

from typing import Annotated, Literal

import numpy as np
from fastapi import FastAPI, Form, HTTPException, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from soniccraft.dsp.effects import apply_fade, apply_gain, normalize_peak, trim_audio
from .services import decode_upload, encode_wav, inspect_upload

app = FastAPI(title="SonicCraft API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(ValueError)
async def invalid_dsp_parameter(_request, error):
    return JSONResponse(status_code=422, content={"detail": str(error)})


@app.exception_handler(RequestValidationError)
async def invalid_request(_request, error):
    messages = [f"{item['loc'][-1]}: {item['msg']}" for item in error.errors()]
    return JSONResponse(status_code=422, content={"detail": "; ".join(messages)})


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


# Synchronous routes run in Starlette's worker thread pool, not the event loop.
@app.post("/api/v1/audio/inspect")
def inspect(file: UploadFile, bins: Annotated[int, Query(ge=16, le=4096)] = 1200):
    return inspect_upload(file, bins)


def wav_response(samples, rate, *, floating=False):
    return Response(
        encode_wav(samples, rate, floating=floating),
        media_type="audio/wav",
        headers={"Content-Disposition": 'attachment; filename="soniccraft.wav"'},
    )


@app.post("/api/v1/audio/process/gain-fade")
def gain_fade(
    file: UploadFile,
    gain_db: Annotated[float, Form(ge=-60, le=24, allow_inf_nan=False)] = 0,
    fade_in_seconds: Annotated[float, Form(ge=0, le=300, allow_inf_nan=False)] = 0,
    fade_out_seconds: Annotated[float, Form(ge=0, le=300, allow_inf_nan=False)] = 0,
    curve: Annotated[Literal["linear", "equal_power", "exponential"], Form()] = "equal_power",
):
    samples, rate, metadata = decode_upload(file)
    if max(fade_in_seconds, fade_out_seconds) > metadata.duration_seconds:
        raise HTTPException(422, "Each fade must fit within the selected track.")
    processed = apply_fade(
        apply_gain(samples, gain_db), rate,
        fade_in_seconds=fade_in_seconds, fade_out_seconds=fade_out_seconds, curve=curve,
    )
    return wav_response(processed, rate, floating=True)


@app.post("/api/v1/audio/process/trim")
def trim(
    file: UploadFile,
    start_sample: Annotated[int, Form(ge=0)],
    end_sample: Annotated[int, Form(gt=0)],
):
    samples, rate, _ = decode_upload(file)
    return wav_response(trim_audio(samples, start_sample, end_sample), rate, floating=True)


@app.post("/api/v1/audio/export")
def export(
    file: UploadFile,
    gain_db: Annotated[float, Form(ge=-120, le=48, allow_inf_nan=False)] = 0,
    normalize: Annotated[bool, Form()] = False,
):
    samples, rate, _ = decode_upload(file)
    samples = apply_gain(samples, gain_db)
    if normalize:
        samples = normalize_peak(samples, -1.0)
    elif float(np.max(np.abs(samples))) > 1.0:
        raise HTTPException(422, "Export would clip. Lower the gain or enable Normalize export.")
    return wav_response(samples, rate)
