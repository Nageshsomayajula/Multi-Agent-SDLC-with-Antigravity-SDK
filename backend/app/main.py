from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import base64
from pathlib import Path
from dotenv import load_dotenv
import httpx
from . import gemini
import aiofiles

load_dotenv(Path(__file__).parent.parent / ".env")

app = FastAPI()

# include Zoom webhook router
from .zoom_webhook import router as zoom_router
app.include_router(zoom_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = Path(Path(__file__).parent.parent, "data")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/")
async def root():
    return {"status": "ok", "message": "Call-attending agent backend"}


@app.get("/auth/google/start")
async def auth_google_start():
    # Placeholder: build Google OAuth URL
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    redirect = os.getenv("REDIRECT_URI")
    scope = "https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/userinfo.email"
    url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code&scope={scope}&redirect_uri={redirect}"
    )
    return RedirectResponse(url)


@app.get("/auth/google/callback")
async def auth_google_callback(code: str = None):
    # Exchange code for tokens (placeholder)
    return JSONResponse({"code": code})


@app.get("/auth/zoom/start")
async def auth_zoom_start():
    client_id = os.getenv("ZOOM_CLIENT_ID")
    redirect = os.getenv("REDIRECT_URI")
    url = f"https://zoom.us/oauth/authorize?response_type=code&client_id={client_id}&redirect_uri={redirect}"
    return RedirectResponse(url)


@app.get("/auth/zoom/callback")
async def auth_zoom_callback(code: str = None):
    return JSONResponse({"code": code})


@app.websocket("/ws/record")
async def websocket_record(ws: WebSocket):
    await ws.accept()
    file_map = {}
    try:
        while True:
            msg = await ws.receive_json()
            # Expect {"filename": "call1.webm", "chunk": "base64...", "final": false}
            filename = msg.get("filename")
            chunk_b64 = msg.get("chunk")
            final = msg.get("final", False)
            if filename not in file_map:
                fpath = STORAGE_DIR / filename
                file_map[filename] = open(fpath, "ab")
            if chunk_b64:
                data = base64.b64decode(chunk_b64)
                file_map[filename].write(data)
            if final:
                file_map[filename].close()
                await ws.send_json({"status": "saved", "filename": filename})
    except WebSocketDisconnect:
        for f in file_map.values():
            try:
                f.close()
            except:
                pass


@app.post("/upload_audio")
async def upload_audio(file: UploadFile = File(...)):
    dest = STORAGE_DIR / file.filename
    async with aiofiles.open(dest, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)
    return {"status": "ok", "filename": file.filename}


@app.post("/transcribe")
async def transcribe(filename: str = Form(...)):
    # Placeholder: send audio to Gemini or another speech-to-text
    fpath = STORAGE_DIR / filename
    if not fpath.exists():
        return JSONResponse({"error": "file not found"}, status_code=404)
    # Read file bytes
    async with aiofiles.open(fpath, 'rb') as fh:
        audio_bytes = await fh.read()

    # Call Gemini STT (or configured STT endpoint)
    try:
        transcript = await gemini.transcribe_audio_bytes(audio_bytes)
    except Exception as e:
        return JSONResponse({"error": "stt_failed", "detail": str(e)}, status_code=500)

    # Call Gemini summarization
    try:
        summary = await gemini.summarize_text(transcript)
    except Exception as e:
        summary = "[summarization failed] " + str(e)

    return {"status": "done", "filename": filename, "transcript": transcript, "summary": summary}
