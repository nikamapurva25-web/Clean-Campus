# main.py
import json
import asyncio
import logging
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS configuration - restrict in production
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the static folder (current directory contains the static files)
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent)), name="static")

# In-memory counts
state = {
    "scanCount": 0,
    "joinCount": 0,
    # optionally per-spot counts: {"spotA": 5}
    "spots": {}
}

# Simple WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast_counts(self):
        payload = json.dumps({
            "type": "counts",
            "scanCount": state["scanCount"],
            "joinCount": state["joinCount"]
        })
        to_remove = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            self.disconnect(ws)

manager = ConnectionManager()

# Serve index (optional redirect to static file)
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        index_path = Path(__file__).parent / "index.html"
        if not index_path.exists():
            logger.error(f"Index file not found: {index_path}")
            return HTMLResponse(content="<h1>Error: index.html not found</h1>", status_code=404)
        html = index_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html)
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>", status_code=500)

# API to register a scan (called when QR page opens)
@app.post("/api/scan")
async def api_scan(spot: str | None = None):
    try:
        state["scanCount"] += 1
        if spot:
            state["spots"].setdefault(spot, 0)
            state["spots"][spot] += 1
        logger.info(f"Scan registered. Total: {state['scanCount']}")
        # broadcast update
        await manager.broadcast_counts()
        return JSONResponse({"scanCount": state["scanCount"]})
    except Exception as e:
        logger.error(f"Error in api_scan: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# API to register "I Stand" clicks
@app.post("/api/join")
async def api_join():
    try:
        state["joinCount"] += 1
        logger.info(f"Join registered. Total: {state['joinCount']}")
        await manager.broadcast_counts()
        return JSONResponse({"joinCount": state["joinCount"]})
    except Exception as e:
        logger.error(f"Error in api_join: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    logger.info(f"WebSocket connected. Active connections: {len(manager.active)}")
    try:
        # send initial counts
        await websocket.send_text(json.dumps({
            "type": "counts",
            "scanCount": state["scanCount"],
            "joinCount": state["joinCount"]
        }))
        while True:
            # keep connection alive; we do not expect messages from client
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected. Active connections: {len(manager.active)}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

