# Call-attending Agent PoC

This workspace contains a proof-of-concept to join Google Meet/Zoom calls and record audio (audio-only), store recordings, and provide hooks to send audio to an LLM (e.g., Gemini) for summarization.

Quick local run (prototype):

1. Backend

Install Python dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Run backend:

```bash
uvicorn backend.app.main:app --reload --port 8000
```

2. Recorder (Google Meet)

Install Node deps (puppeteer):

```bash
cd tools
npm init -y
npm install puppeteer
```

Run recorder (open browser and inject recorder):

```bash
node meet_recorder.js "https://meet.google.com/your-meet" "ws://localhost:8000/ws/record" call1.webm
```

Notes & next steps:
- You must obtain OAuth credentials for Google and Zoom and place them in `backend/.env`.
- The puppeteer recorder uses `getDisplayMedia` to capture audio; run non-headless and grant screen/audio capture permissions.
- The backend has placeholder endpoints to exchange OAuth codes and to call Gemini — you'll need to implement the final integration with Google/Zoom APIs and Gemini speech/text endpoints.

Production-grade recording and deployment
--------------------------------------

This repo includes scaffolding for production:

- `docker-compose.yml` runs the `backend` plus a Janus Gateway (`meetecho/janus-gateway`) for server-side WebRTC recording and `redis` for coordination. Use Janus to accept incoming WebRTC streams from a browser or headless client and record them server-side.
- `backend/Dockerfile` builds the backend container.
- `backend/zoom_webhook.py` provides a `/zoom/webhook` endpoint to receive Zoom cloud-recording webhooks and download completed recordings.
- `k8s/` contains simple `backend-deployment.yaml` and `backend-service.yaml` manifests to deploy the backend to Kubernetes (adapt image names, secrets, and configs).

Recommendations for production:

- Use provider cloud recording when possible: Zoom Cloud Recording webhooks (and automatic downloads) are the most reliable. Google Meet recordings in Google Workspace are saved to Drive; subscribe to Calendar events and check Drive for recordings.
- For low-latency recording under your control, run a robust SFU (mediasoup, Janus, Jitsi) in front of the backend to accept client WebRTC streams and record mixes or per-participant tracks.
- Store recordings in object storage (S3/GCS) and process asynchronously for transcription/summarization.
- Use a secure OAuth token store and rotate keys; store secrets in Kubernetes Secrets or a secrets manager.

Deployment quick tips:

1. Build and push backend image:

```bash
docker build -t your-registry/call-agent-backend:latest -f backend/Dockerfile backend
docker push your-registry/call-agent-backend:latest
```

2. Apply k8s manifests (after creating `call-agent-secrets`):

```bash
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml
```

# Multi-Agent-SDLC-with-Antigravity-SDK