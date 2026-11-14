"""Same-origin UI and one authoritative in-memory connection hub."""

from contextlib import asynccontextmanager
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from .connections import Hub

ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = ROOT / "apps" / "web" / "dist"


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.hub = Hub()
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="LineOfSight foundation", lifespan=lifespan)

    @application.get("/health")
    async def health():
        return {"v": 1, "ok": True, "run_id": application.state.hub.run_id}

    @application.websocket("/v1/events")
    async def events(socket: WebSocket):
        await socket.accept()
        hub = application.state.hub
        client, error = hub.bind(socket, socket.query_params.get("role"), socket.query_params.get("id"))
        if error:
            await socket.send_json({"v": 1, "type": "ERROR", "run_id": hub.run_id,
                                    "error": "connection_rejected", "message": error})
            await socket.close(code=4409 if "already active" in error else 4400)
            return
        try:
            await hub.broadcast()
            while True:
                message = await socket.receive()
                if message["type"] == "websocket.disconnect":
                    break
                try:
                    if "text" not in message:
                        raise ValueError
                    event = json.loads(message["text"])
                except (ValueError, TypeError):
                    await hub.error(client, "invalid_event", "Send a text JSON object.")
                    continue
                changed, failure = hub.apply_event(client, event)
                if failure:
                    await hub.error(client, *failure)
                elif changed:
                    await hub.broadcast()
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass
        finally:
            if hub.unbind(client):
                await hub.broadcast()

    @application.get("/", include_in_schema=False)
    async def home():
        return RedirectResponse("/expense")

    @application.get("/expense", include_in_schema=False)
    @application.get("/json", include_in_schema=False)
    @application.get("/operator", include_in_schema=False)
    @application.get("/fixture-mobile", include_in_schema=False)
    async def target_page():
        index = WEB_DIST / "index.html"
        if not index.is_file():
            raise HTTPException(503, "Web build missing. Run: npm --prefix apps/web run build")
        return FileResponse(index, headers={"Cache-Control": "no-store"})

    application.mount("/fixtures", StaticFiles(directory=ROOT / "fixtures"), name="fixtures")
    application.mount(
        "/markers", StaticFiles(directory=ROOT / "apps/web/public/markers"), name="markers"
    )
    application.mount(
        "/assets", StaticFiles(directory=WEB_DIST / "assets", check_dir=False), name="assets"
    )
    return application


app = create_app()
