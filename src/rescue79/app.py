"""Local FastAPI application for the Rescue79 still-image reviewer."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .inference import ReviewError, Runtime

PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
MAX_MULTIPART_BYTES = MAX_IMAGE_BYTES + 512 * 1024


def _resolve_model_path() -> Path:
    """Find the bundled model in an editable checkout or an installed wheel."""

    filename = "rescue79-hard4-portable-v1.pt"
    candidates = (
        PACKAGE_DIR.parents[1] / "models" / filename,
        PACKAGE_DIR.parent / "models" / filename,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


MODEL_PATH = _resolve_model_path()


@lru_cache(maxsize=1)
def runtime() -> Runtime:
    return Runtime(MODEL_PATH)


app = FastAPI(
    title="Rescue79 정적 7·9 모델 검토기",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _same_origin(request: Request) -> bool:
    """Reject cross-site POSTs even though the service is loopback-only."""

    origin = request.headers.get("origin")
    if not origin:
        return True
    expected = f"{request.url.scheme}://{request.headers.get('host', '')}"
    return origin.rstrip("/") == expected.rstrip("/")


@app.middleware("http")
async def safety_headers(request: Request, call_next):
    if request.url.path == "/api/review":
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        # ``testserver`` is Starlette's in-process TestClient host, never a
        # network listener. The CLI binds only to 127.0.0.1.
        if host not in {"127.0.0.1", "localhost", "testserver"}:
            return JSONResponse(status_code=403, content={"detail": "로컬 요청만 허용합니다."})
        if not _same_origin(request):
            return JSONResponse(
                status_code=403,
                content={"detail": "다른 웹사이트에서 보낸 요청을 차단했습니다."},
            )
        content_length = request.headers.get("content-length")
        if content_length is None:
            return JSONResponse(
                status_code=411,
                content={"detail": "사진 크기를 먼저 확인할 수 없는 요청은 받지 않습니다."},
            )
        try:
            body_bytes = int(content_length)
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "잘못된 요청 크기입니다."})
        if body_bytes < 0 or body_bytes > MAX_MULTIPART_BYTES:
            return JSONResponse(status_code=413, content={"detail": "사진은 12MB 이하만 가능합니다."})
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data: blob:; "
        "style-src 'self'; script-src 'self'; connect-src 'self'; "
        "object-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    return response


@app.exception_handler(ReviewError)
async def review_error_handler(_request, exc: ReviewError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    try:
        return runtime().metadata()
    except ReviewError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/review")
async def review(
    request: Request,
    expected_digit: str = Form(...),
    image: UploadFile = File(...),
) -> dict:
    content_type = (image.content_type or "").lower()
    if content_type not in {"image/png", "image/jpeg", "image/webp"}:
        raise HTTPException(status_code=415, detail="PNG, JPG 또는 WEBP 사진만 가능합니다.")
    payload = await image.read(MAX_IMAGE_BYTES + 1)
    await image.close()
    if not payload:
        raise HTTPException(status_code=422, detail="사진 파일이 비어 있습니다.")
    if len(payload) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="사진은 12MB 이하만 가능합니다.")
    return runtime().review(payload, expected_digit)
