"""Same-origin UI and one authoritative in-memory connection hub."""

from contextlib import asynccontextmanager
from pathlib import Path
import json

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import UploadFile

from .connections import Hub
from .vision.detection import MAX_BYTES, ImageTooLarge, validate_jpeg
from .vision.service import FrameRejected, VisionService

ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = ROOT / "apps" / "web" / "dist"


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.hub = Hub()
    vision = VisionService(application.state.hub)
    application.state.hub.vision = vision
    vision.start()
    try:
        yield
    finally:
        await vision.close()


def create_app() -> FastAPI:
    application = FastAPI(title="LineOfSight foundation", lifespan=lifespan)

    @application.middleware("http")
    async def reject_large_frame_body(request, call_next):
        if request.url.path == "/v1/frames":
            length = request.headers.get("content-length")
            if length and (not length.isdigit() or int(length) > MAX_BYTES + 64_000):
                return JSONResponse({"detail": "Frame request is too large or has an invalid length."}, status_code=413)
        return await call_next(request)

    @application.get("/health")
    async def health():
        return {"v": 1, "ok": True, "run_id": application.state.hub.run_id}

    @application.post("/v1/frames", status_code=202)
    async def frames(request: Request):
        vision = application.state.hub.vision
        async with request.form(max_files=1, max_fields=4, max_part_size=1024) as form:
            if set(form) != {"run_id", "stream_id", "frame_seq", "age_ms", "image"} or len(list(form.multi_items())) != 5:
                raise HTTPException(400, "Send exactly run_id, stream_id, frame_seq, age_ms, and image.")
            image = form["image"]
            if not isinstance(image, UploadFile):
                raise HTTPException(400, "image must be a JPEG file part.")
            try:
                if not all(isinstance(form[key], str) for key in ("run_id", "stream_id", "frame_seq", "age_ms")):
                    raise ValueError
                sequence, age_ms = int(form["frame_seq"]), int(form["age_ms"])
            except (ValueError, TypeError):
                raise HTTPException(422, "Frame sequence and age must be integers.")
            try:
                owner = vision.guard(form["run_id"], form["stream_id"], sequence, age_ms)
                data = await image.read(MAX_BYTES + 1)
                validate_jpeg(data)
                vision.submit(form["run_id"], form["stream_id"], sequence, age_ms, data, owner)
            except FrameRejected as error:
                raise HTTPException(error.status, str(error))
            except ImageTooLarge as error:
                raise HTTPException(413, str(error))
            except ValueError as error:
                raise HTTPException(400, str(error))
            return {"accepted": True, "stream_id": form["stream_id"], "frame_seq": sequence}

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
