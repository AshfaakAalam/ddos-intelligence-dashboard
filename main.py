"""FastAPI application for the DDoS Intelligence dashboard."""
import asyncio
import logging
import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from werkzeug.security import check_password_hash, generate_password_hash

from cloudflare import get_attack_data
from database import SessionLocal, User, get_latest_snapshot, save_snapshot
from processor import process_attack_data

BASE_DIR = Path(__file__).resolve().parent
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("ddos_dashboard")
POLL_INTERVAL_SECONDS = max(60, int(os.getenv("POLL_INTERVAL_SECONDS", "300")))

state = {
    "attacks": [], "source_country_count": 0, "target_country_count": 0,
    "attack_count": 0, "last_updated": None, "source_timestamp": None,
    "status": "waiting", "error": None,
}
clients = set()
poller_started = False
refresh_lock = asyncio.Lock()


def _source_timestamp(payload):
    result = payload.get("result") or {}
    meta = payload.get("meta") or result.get("meta") or {}
    for key in ("date", "timestamp", "lastUpdated", "last_updated"):
        if meta.get(key):
            return str(meta[key])
    return None


def _apply_payload(payload, fetched_at=None, source_timestamp=None, persist=True):
    attacks = process_attack_data(payload)
    sources = {a["source"] for a in attacks if a.get("source")}
    targets = {a["target"] for a in attacks if a.get("target")}
    fetched_at = fetched_at or datetime.now(timezone.utc).isoformat()
    source_timestamp = source_timestamp or _source_timestamp(payload)
    if persist:
        try:
            save_snapshot(payload, len(attacks), source_timestamp)
        except Exception:
            logger.exception("Could not persist the Cloudflare snapshot")
    state.update({
        "attacks": attacks,
        "source_country_count": len(sources),
        "target_country_count": len(targets),
        "attack_count": len(attacks),
        "last_updated": fetched_at,
        "source_timestamp": source_timestamp,
        "status": "live" if attacks else "no_data",
        "error": None,
    })


async def refresh_data():
    async with refresh_lock:
        try:
            payload = await asyncio.to_thread(get_attack_data)
            _apply_payload(payload)
            await broadcast_state()
        except Exception as exc:
            logger.warning("Cloudflare refresh failed: %s", exc)
            state["error"] = str(exc)
            state["status"] = "error" if state["last_updated"] is None else "stale"
            await broadcast_state()
        return public_state()


def public_state():
    return {
        "attacks": state["attacks"],
        "source_country_count": state["source_country_count"],
        "target_country_count": state["target_country_count"],
        "attack_count": state["attack_count"],
        "last_updated": state["last_updated"],
        "source_timestamp": state["source_timestamp"],
        "status": state["status"],
        "error": state["error"],
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
        "data_note": "Aggregated Cloudflare Radar country-level data; not individual packets or source IPs.",
    }


async def broadcast_state():
    if not clients:
        return
    payload = public_state()
    stale_clients = []
    for client in tuple(clients):
        try:
            await client.send_json(payload)
        except Exception:
            stale_clients.append(client)
    for client in stale_clients:
        clients.discard(client)


async def poll_loop():
    # Load last successful snapshot first so the dashboard has data between restarts.
    try:
        cached = await asyncio.to_thread(get_latest_snapshot)
        if cached:
            _apply_payload(
                cached["payload"], cached["fetched_at"], cached["source_timestamp"], persist=False
            )
            state["status"] = "stale"
    except Exception:
        logger.exception("Could not load the previous snapshot")
    while True:
        await refresh_data()
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global poller_started
    poller_started = True
    task = asyncio.create_task(poll_loop())
    yield
    poller_started = False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="DDoS Intelligence", version="2.0.0", lifespan=lifespan)
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_urlsafe(32)
if not os.getenv("SESSION_SECRET"):
    logger.warning("SESSION_SECRET is unset; generated an ephemeral development secret. Set SESSION_SECRET in .env.")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=os.getenv("COOKIE_SECURE", "false").lower() == "true",
)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/")
async def home(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request=request, name="index.html")


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")


@app.post("/register")
async def register(request: Request, username: str = Form(...), email: str = Form(...), password: str = Form(...)):
    username, email = username.strip(), email.strip().lower()
    if len(username) < 3 or len(password) < 8:
        return templates.TemplateResponse(
            request=request, name="register.html",
            context={"error": "Username must be at least 3 characters and password at least 8 characters."},
            status_code=400,
        )
    db = SessionLocal()
    try:
        if db.query(User).filter((User.username == username) | (User.email == email)).first():
            return templates.TemplateResponse(
                request=request, name="register.html",
                context={"error": "Username or email is already registered."}, status_code=409,
            )
        db.add(User(username=username, email=email, password_hash=generate_password_hash(password)))
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/login", status_code=303)


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username.strip()).first()
        if not user or not check_password_hash(user.password_hash, password):
            return templates.TemplateResponse(
                request=request, name="login.html",
                context={"error": "Invalid username or password"}, status_code=401,
            )
        request.session.clear()
        request.session["user_id"] = user.id
        request.session["username"] = user.username
    finally:
        db.close()
    return RedirectResponse("/dashboard", status_code=303)


@app.get("/dashboard")
async def dashboard(request: Request):
    if not request.session.get("user_id"):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        request=request, name="dashboard.html",
        context={"username": request.session.get("username", "Analyst")},
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ddos-intelligence"}


@app.get("/api/attacks")
async def attacks(request: Request, refresh: bool = False):
    if refresh or (state["last_updated"] is None and not poller_started and not refresh_lock.locked()):
        await refresh_data()
    return public_state()


@app.websocket("/ws/attacks")
async def attacks_websocket(websocket: WebSocket):
    if not websocket.session.get("user_id"):
        await websocket.close(code=1008)
        return
    await websocket.accept()
    clients.add(websocket)
    try:
        await websocket.send_json(public_state())
        while True:
            # Keep connection alive; browser may send pings.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)
