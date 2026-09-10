from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .devices import list_devices
from .mic_test import LiveMicTestManager
from .session import SessionManager
from .websocket import WebSocketHub


hub = WebSocketHub()
manager = SessionManager(settings, hub.publish_from_thread)
mic_tester = LiveMicTestManager(settings, hub.publish_from_thread)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    hub.set_loop(asyncio.get_running_loop())
    yield
    mic_tester.stop()
    manager.stop()


app = FastAPI(title="STT Local", lifespan=lifespan)


class StartSessionRequest(BaseModel):
    mic_a: int
    speaker_a: int
    mic_b: int
    speaker_b: int


class StartMicTestRequest(BaseModel):
    device_id: int
    label: str
    language: str | None = None


@app.get("/api/devices")
def get_devices():
    return {"devices": list_devices()}


@app.get("/api/status")
def get_status():
    return {**manager.status(), "mic_test": mic_tester.status()}


@app.post("/api/mic-test/start")
def start_mic_test(request: StartMicTestRequest):
    if manager.status()["running"]:
        raise HTTPException(status_code=409, detail="Hentikan sesi interkom sebelum menguji mic.")
    try:
        return mic_tester.start(**request.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Tidak dapat menguji mic: {exc}") from exc


@app.post("/api/mic-test/stop")
def stop_mic_test():
    return mic_tester.stop()


@app.post("/api/session/start")
def start_session(request: StartSessionRequest):
    try:
        mic_tester.stop()
        return manager.start(**request.model_dump())
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/session/stop")
def stop_session():
    return manager.stop()


@app.get("/api/sessions/{session_id}/txt")
def download_txt(session_id: str):
    path = settings.sessions_dir / f"{session_id}.txt"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Hasil TXT tidak ditemukan.")
    return FileResponse(path, media_type="text/plain; charset=utf-8", filename=path.name)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await hub.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        hub.disconnect(websocket)


app.mount("/", StaticFiles(directory=settings.frontend_dir, html=True), name="frontend")
