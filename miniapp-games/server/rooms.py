"""Matchmaking va xonalar. Sof mantiq: har bir ochiq metod [(user_id, xabar), ...] qaytaradi."""
import copy, random, time

from server.games.base import Game

CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def safe(f):
    def w(self, u, *a):
        try:
            return f(self, u, *a)
        except ValueError as e:
            return [(u["id"], {"t": "err", "msg": str(e)})]
    return w


class Room:
    def __init__(self, rid, game, host=None, mode="queue"):
        self.id, self.game, self.host, self.code, self.mode = rid, game, host, None, mode
        self.seats, self.state, self.status, self.res = [], None, "waiting", None
        self.last = time.time()


class Hub:
    def __init__(self, registry, record=None, allowed=None, profile=None):
        self.reg = registry
        self.profile = profile or (lambda uid, gid: {})
        self.record = record or (lambda *a: None)
        self.allowed = allowed or (lambda gid: True)
        self.rooms, self.codes, self.user_room, self.queues, self._n = {}, {}, {}, {}, 0

    # ---------- ichki yordamchilar
    def _game(self, gid):
        g = self.reg.games.get(gid)
        if not g or not self.allowed(gid):
            raise ValueError("O'yin mavjud emas")
        return g

    def _free(self, uid):
        if uid in self.user_room:
            raise ValueError("Avval joriy o'yindan chiqing")

    def _new(self, g, host=None, mode="queue"):
        self._n += 1
        r = Room(f"r{self._n}", g, host, mode)
        self.rooms[r.id] = r
        return r

    def _sit(self, r, u, bot=False):
        r.seats.append({"id": None if bot else u["id"], "name": u["name"], "bot": bot,
                        "prof": {} if bot else self.profile(u["id"], r.game.id)})
        if not bot:
            self.user_room[u["id"]] = r.id

    def _room_of(self, u):
        return self.rooms.get(self.user_room.get(u["id"]))

    def _seat(self, r, u):
        return next(i for i, p in enumerate(r.seats) if p["id"] == u["id"])

    def _msg(self, r, i):
        g, live = r.game, r.state is not None
        return {"t": "room", "id": r.id, "game": g.id, "status": r.status, "code": r.code, "host": r.host,
                "seats": [{"name": p["name"], "bot": p["bot"], **p.get("prof", {})} for p in r.seats], "you": i,
                "mode": r.mode,
                "min": g.min_players, "max": g.max_players,
                "view": g.view(r.state, i) if live else None,
                "turn": g.turn(r.state) if live and not r.res else None, "result": r.res}

    def _cast(self, r):
        return [(p["id"], self._msg(r, i)) for i, p in enumerate(r.seats)
                if not p["bot"] and self.user_room.get(p["id"]) == r.id]

    def _start(self, r):
        random.shuffle(r.seats)
        r.state, r.status = r.game.new(len(r.seats)), "playing"
        return self._after(r)

    def _after(self, r):
        r.last = time.time()
        res = r.game.result(r.state)
        if res:
            self._finish(r, res)
        return self._cast(r)

    def _finish(self, r, res):
        res = dict(res)
        out = self.record(r.game.id, [dict(p) for p in r.seats], res, r.mode)
        if out and any(out):
            res["rating"] = out
        r.res, r.status = res, "over"

    def _drop(self, r):
        self.rooms.pop(r.id, None)
        self.codes.pop(r.code, None)
        for p in r.seats:
            if not p["bot"] and self.user_room.get(p["id"]) == r.id:
                self.user_room.pop(p["id"])

    def _play(self, r, seat, mv):
        st = copy.deepcopy(r.state)   # noqonuniy yurish holatni buzib qo'ymasin
        r.game.apply(st, seat, mv if isinstance(mv, dict) else {})
        r.state = st

    # ---------- ochiq API
    @safe
    def enter(self, u):
        r = self._room_of(u)
        if not r:
            return [(u["id"], {"t": "idle"})]
        return [(u["id"], self._msg(r, self._seat(r, u)))]

    @safe
    def queue(self, u, gid):
        g = self._game(gid)
        self._free(u["id"])
        self.cancel(u)
        q = self.queues.setdefault(gid, [])
        q.append(u)
        if len(q) < g.min_players:
            return [(u["id"], {"t": "queued", "game": gid})]
        r = self._new(g)
        for x in q[:g.min_players]:
            self._sit(r, x)
        del q[:g.min_players]
        return self._start(r)

    def cancel(self, u):
        for q in self.queues.values():
            q[:] = [x for x in q if x["id"] != u["id"]]
        return [(u["id"], {"t": "idle"})]

    @safe
    def bot(self, u, gid):
        g = self._game(gid)
        self._free(u["id"])
        if type(g).bot_move is Game.bot_move:
            raise ValueError("Bu o'yinda robot yo'q")
        r = self._new(g, u["id"], "bot")
        self._sit(r, u)
        for _ in range(g.min_players - 1):
            self._sit(r, {"name": "🤖 Robot"}, bot=True)
        return self._start(r)

    @safe
    def create(self, u, gid):
        g = self._game(gid)
        self._free(u["id"])
        r = self._new(g, u["id"], "friend")
        while True:
            r.code = "".join(random.choices(CODE_CHARS, k=5))
            if r.code not in self.codes:
                break
        self.codes[r.code] = r.id
        self._sit(r, u)
        return self._cast(r)

    @safe
    def join(self, u, code):
        self._free(u["id"])
        r = self.rooms.get(self.codes.get(str(code).strip().upper()))
        if not r or r.status != "waiting":
            raise ValueError("Xona topilmadi")
        self._sit(r, u)
        return self._start(r) if len(r.seats) >= r.game.max_players else self._cast(r)

    @safe
    def start(self, u):
        r = self._room_of(u)
        if not r or r.status != "waiting" or r.host != u["id"]:
            raise ValueError("Boshlab bo'lmaydi")
        if len(r.seats) < r.game.min_players:
            raise ValueError("O'yinchilar yetarli emas")
        return self._start(r)

    @safe
    def move(self, u, mv):
        r = self._room_of(u)
        if not r or r.status != "playing":
            raise ValueError("O'yin boshlanmagan")
        self._play(r, self._seat(r, u), mv)
        return self._after(r)

    def leave(self, u):
        self.cancel(u)
        out = [(u["id"], {"t": "idle"})]
        r = self._room_of(u)
        self.user_room.pop(u["id"], None)
        if not r:
            return out
        seat = next((i for i, p in enumerate(r.seats) if p["id"] == u["id"]), None)
        if r.status == "playing":
            self._finish(r, {"winner": (1 - seat) if len(r.seats) == 2 else None, "reason": "leave", "left": seat})
        elif r.status == "waiting":
            if r.host == u["id"]:   # xona egasi chiqsa xona yopiladi
                out += [(p["id"], {"t": "idle", "msg": "Xona yopildi"}) for p in r.seats
                        if p["id"] != u["id"] and not p["bot"]]
                self._drop(r)
                return out
            r.seats = [p for p in r.seats if p["id"] != u["id"]]
        humans = [p for p in r.seats if not p["bot"] and self.user_room.get(p["id"]) == r.id]
        if not humans:
            self._drop(r)
            return out
        return out + self._cast(r)

    # ---------- robot
    def _bot_turn(self, r):
        if r.status != "playing" or r.res:
            return None
        t = r.game.turn(r.state)
        return t if t is not None and r.seats[t]["bot"] else None

    def needs_bot(self, rid):
        r = self.rooms.get(rid)
        return bool(r) and self._bot_turn(r) is not None

    def bot_step(self, rid):
        r = self.rooms.get(rid)
        t = self._bot_turn(r) if r else None
        if t is None:
            return []
        self._play(r, t, r.game.bot_move(r.state, t))
        return self._after(r)

    # ---------- eskirgan xonalar
    def reap(self, now=None, idle=900):
        now, out = now or time.time(), []
        for r in list(self.rooms.values()):
            if now - r.last < idle:
                continue
            if r.status == "playing":
                t = r.game.turn(r.state)
                two = len(r.seats) == 2 and t is not None
                self._finish(r, {"winner": (1 - t) if two else None, "reason": "timeout", "left": t})
                r.last = now
                out += self._cast(r)
            else:
                out += [(p["id"], {"t": "idle", "msg": "Xona yopildi"}) for p in r.seats
                        if not p["bot"] and self.user_room.get(p["id"]) == r.id]
                self._drop(r)
        return out
