from fastapi import APIRouter, Request, BackgroundTasks
import httpx
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

router = APIRouter()


@router.post('/zoom/webhook')
async def zoom_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    # Zoom will send various event types; handle 'recording.completed'
    event = data.get('event')
    if event == 'recording.completed':
        payload = data.get('payload', {})
        recording_files = payload.get('object', {}).get('recording_files', [])
        # process each recording file in background
        for rf in recording_files:
            download_url = rf.get('download_url')
            filename = rf.get('id') + '.mp4'
            background_tasks.add_task(download_recording, download_url, filename)
    return {'status': 'ok'}


async def download_recording(url: str, filename: str):
    # Zoom download URL may require JWT or OAuth access token — placeholder
    headers = {}
    token = os.getenv('ZOOM_JWT') or os.getenv('ZOOM_OAUTH_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        outdir = Path(__file__).parent.parent / 'data'
        outdir.mkdir(parents=True, exist_ok=True)
        dest = outdir / filename
        with open(dest, 'wb') as fh:
            fh.write(resp.content)
