"""K0 foundation: health and a same-origin fixture UI; no workflow yet."""

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
WEB_DIST = ROOT / "apps" / "web" / "dist"


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.run_id = str(uuid4())
    application.state.drafts = {"expenses": None, "json": None}
    yield


def create_app() -> FastAPI:
    application = FastAPI(title="LineOfSight foundation", lifespan=lifespan)

    @application.get("/health")
    async def health():
        return {"v": 1, "ok": True, "run_id": application.state.run_id}

    @application.get("/", include_in_schema=False)
    async def home():
        return RedirectResponse("/expense")

    @application.get("/expense", include_in_schema=False)
    @application.get("/json", include_in_schema=False)
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
