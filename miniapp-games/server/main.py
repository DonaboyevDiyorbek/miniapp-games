import asyncio, json, os, time, traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from server import auth
from server.db import DB
from server.games.base import Game
from server.registry import Registry
from server.rooms import Hub

ROOT = Path(__file__).resolve().parent.parent
TOKEN = os.getenv("BOT_TOKEN", "")
ADMINS = {int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x}
DEV = os.getenv("DEV") == "1"
ALLOW_UPLOAD = os.getenv("ALLOW_PLUGIN_UPLOAD") == "1"

db = DB(os.getenv("DB_PATH", "games.db"))
reg = Registry()
reg.load()
db.sync_games(reg.meta)
hub = Hub(reg, record=db.record, allowed=db.is_enabled, profile=db.profile)
conns: dict[int, WebSocket] = {}
tasks, bots = set(), set()


def who(init: str):
    if DEV and init.startswith("dev:"):
        parts = (init.split(":", 2) + ["", ""])[:3]
        try:
            return {"id": int(parts[1]), "name": parts[2] or f"Dev{parts[1]}"}
        except ValueError:
            return None
    return auth.validate(init, TOKEN)


async def push(msgs):
    for uid, m in msgs:
        ws = conns.get(uid)
        if ws:
            try:
                await ws.send_text(json.dumps(m, ensure_ascii=False))
            except Exception:
                pass


def spawn(coro):
    t = asyncio.create_task(coro)
    tasks.add(t)
    t.add_done_callback(tasks.discard)


async def run_bots(rid):
    if rid in bots:
        return
    bots.add(rid)
    try:
        while hub.needs_bot(rid):
            await asyncio.sleep(0.8)
            await push(hub.bot_step(rid))
    except Exception:
        traceback.print_exc()
    finally:
        bots.discard(rid)


async def reaper():
    while True:
        await asyncio.sleep(30)
        await push(hub.reap())


@asynccontextmanager
async def lifespan(app):
    t = asyncio.create_task(reaper())
    yield
    t.cancel()


app = FastAPI(lifespan=lifespan)


async def handle(u, m):
    g = m.get("game")
    f = {"queue": lambda: hub.queue(u, g), "cancel": lambda: hub.cancel(u), "bot": lambda: hub.bot(u, g),
         "create": lambda: hub.create(u, g), "join": lambda: hub.join(u, m.get("code", "")),
         "start": lambda: hub.start(u), "move": lambda: hub.move(u, m.get("move")),
         "leave": lambda: hub.leave(u)}.get(m.get("t"))
    if not f:
        return
    await push(f())
    rid = hub.user_room.get(u["id"])
    if rid and hub.needs_bot(rid):
        spawn(run_bots(rid))


@app.websocket("/ws")
async def ws_endpoint(sock: WebSocket):
    await sock.accept()
    u = who(sock.query_params.get("init", ""))
    if not u:
        await sock.close(4401)
        return
    db.upsert_user(u["id"], u["name"])
    old = conns.get(u["id"])
    conns[u["id"]] = sock
    if old:
        try:
            await old.close()
        except Exception:
            pass
    await push(hub.enter(u))
    try:
        while True:
            try:
                m = json.loads(await sock.receive_text())
            except json.JSONDecodeError:
                continue
            try:
                await handle(u, m if isinstance(m, dict) else {})
            except Exception:
                traceback.print_exc()
    except WebSocketDisconnect:
        pass
    finally:
        if conns.get(u["id"]) is sock:
            conns.pop(u["id"], None)


# ---------- REST
@app.get("/api/games")
def games():
    return [{**r, "min": reg.games[r["id"]].min_players, "max": reg.games[r["id"]].max_players,
             "bot": type(reg.games[r["id"]]).bot_move is not Game.bot_move}
            for r in db.catalog() if r["id"] in reg.games]


@app.get("/api/me")
def me(req: Request):
    u = who(req.headers.get("x-init-data", ""))
    if not u:
        raise HTTPException(401, "Telegram orqali oching")
    return {**u, "admin": u["id"] in ADMINS, "ratings": {g["id"]: db.profile(u["id"], g["id"]) for g in db.catalog()}}


@app.get("/api/leaderboard")
def leaderboard(game: str, req: Request):
    u = who(req.headers.get("x-init-data", ""))
    if not u:
        raise HTTPException(401, "Telegram orqali oching")
    if game not in reg.games or not db.is_enabled(game):
        raise HTTPException(404, "O'yin topilmadi")
    return {"top": db.leaderboard(game, 500), "me": db.profile(u["id"], game)}


@app.get("/plugins/{gid}/client.js")
def plugin_js(gid: str):
    if gid not in reg.games:
        raise HTTPException(404)
    return FileResponse(reg.dir / gid / "client.js", media_type="text/javascript")


def admin(req: Request):
    u = who(req.headers.get("x-init-data", ""))
    if not u or u["id"] not in ADMINS:
        raise HTTPException(403, "Admin emas")
    return u


class GameIn(BaseModel):
    enabled: bool | None = None
    sort: int | None = None
    title: str | None = Field(None, max_length=40)
    icon: str | None = Field(None, max_length=8)


@app.get("/api/admin/games")
def admin_games(req: Request):
    admin(req)
    return {"games": [{**r, "loaded": r["id"] in reg.games} for r in db.catalog(False)], "can_upload": ALLOW_UPLOAD}


@app.post("/api/admin/games/{gid}")
def admin_update(gid: str, body: GameIn, req: Request):
    admin(req)
    d = body.model_dump()
    if d["enabled"] is not None:
        d["enabled"] = int(d["enabled"])
    db.update_game(gid, **d)
    return {"ok": True}


@app.post("/api/admin/plugins")
async def admin_upload(req: Request, file: UploadFile = File(...)):
    admin(req)
    if not ALLOW_UPLOAD:
        raise HTTPException(403, "Yuklash o'chirilgan (ALLOW_PLUGIN_UPLOAD=1)")
    data = await file.read(2_000_001)
    if len(data) > 2_000_000:
        raise HTTPException(400, "Fayl katta")
    try:
        gid = reg.install_zip(data)
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.sync_games(reg.meta)
    return {"ok": True, "id": gid}


app.mount("/", StaticFiles(directory=ROOT / "web", html=True), name="web")
