import json, sqlite3, time

FIELDS = {"enabled", "sort", "title", "icon"}
START_RATING, FRIEND_EVERY = 1000, 5


class DB:
    def __init__(self, path=":memory:"):
        self.c = sqlite3.connect(path, check_same_thread=False)
        self.c.row_factory = sqlite3.Row
        self.c.executescript("""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, seen INTEGER);
CREATE TABLE IF NOT EXISTS games(id TEXT PRIMARY KEY, enabled INTEGER DEFAULT 1, sort INTEGER DEFAULT 0, title TEXT, icon TEXT);
CREATE TABLE IF NOT EXISTS results(id INTEGER PRIMARY KEY AUTOINCREMENT, game TEXT, players TEXT, winner INTEGER, reason TEXT, mode TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS ratings(user_id INTEGER, game TEXT, rating INTEGER, played INTEGER, wins INTEGER, losses INTEGER,
  draws INTEGER, friend_games INTEGER, PRIMARY KEY(user_id, game));
""")

    # ---------- foydalanuvchilar va katalog
    def upsert_user(self, uid, name):
        self.c.execute("INSERT INTO users VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, seen=excluded.seen",
                       (uid, name, int(time.time())))
        self.c.commit()

    def sync_games(self, meta):
        """Yangi topilgan plaginlarni katalogga qo'shadi (manifest `default_enabled: false` bo'lsa o'chiq holda)."""
        nxt = self.c.execute("SELECT COALESCE(MAX(sort),0) FROM games").fetchone()[0] + 1
        for gid, m in meta.items():
            if not self.c.execute("SELECT 1 FROM games WHERE id=?", (gid,)).fetchone():
                self.c.execute("INSERT INTO games VALUES(?,?,?,?,?)",
                               (gid, int(m.get("default_enabled", True)), nxt, m.get("name", gid), m.get("icon", "🎮")))
                nxt += 1
        self.c.commit()

    def catalog(self, only_enabled=True):
        q = "SELECT * FROM games" + (" WHERE enabled=1" if only_enabled else "") + " ORDER BY sort, id"
        return [dict(r) for r in self.c.execute(q).fetchall()]

    def is_enabled(self, gid):
        r = self.c.execute("SELECT enabled FROM games WHERE id=?", (gid,)).fetchone()
        return bool(r and r[0])

    def update_game(self, gid, **kw):
        kw = {k: v for k, v in kw.items() if k in FIELDS and v is not None}
        if kw:
            self.c.execute("UPDATE games SET " + ",".join(f"{k}=?" for k in kw) + " WHERE id=?", (*kw.values(), gid))
            self.c.commit()

    # ---------- reyting (Elo, har bir o'yin uchun alohida)
    def _row(self, uid, gid):
        r = self.c.execute("SELECT * FROM ratings WHERE user_id=? AND game=?", (uid, gid)).fetchone()
        return dict(r) if r else {"user_id": uid, "game": gid, "rating": START_RATING, "played": 0, "wins": 0,
                                  "losses": 0, "draws": 0, "friend_games": 0}

    def profile(self, uid, gid):
        """{"rating", "rank"}: rank faqat reytingli o'yin o'ynagan o'yinchida bo'ladi."""
        r = self._row(uid, gid)
        rank = None
        if r["played"]:
            rank = self.c.execute(
                "SELECT COUNT(*)+1 FROM ratings WHERE game=? AND played>0 AND (rating>? OR (rating=? AND played>?) "
                "OR (rating=? AND played=? AND user_id<?))",
                (gid, r["rating"], r["rating"], r["played"], r["rating"], r["played"], uid)).fetchone()[0]
        return {"rating": r["rating"], "rank": rank}

    def leaderboard(self, gid, limit=500):
        rows = self.c.execute(
            "SELECT r.user_id AS id, COALESCE(u.name,'?') AS name, r.rating, r.played, r.wins, r.losses, r.draws "
            "FROM ratings r LEFT JOIN users u ON u.id=r.user_id WHERE r.game=? AND r.played>0 "
            "ORDER BY r.rating DESC, r.played DESC, r.user_id ASC LIMIT ?", (gid, limit)).fetchall()
        return [{"rank": i + 1, **dict(r)} for i, r in enumerate(rows)]

    def record(self, game, seats, res, mode="queue"):
        """Natijani saqlaydi, reytingni yangilaydi. Har bir o'rindiq uchun {"before","after","counted","next"} yoki None.
        Qoidalar: robot bilan o'yin reytingga ta'sir qilmaydi; tasodifiy raqib bilan har doim hisoblanadi;
        do'st bilan o'yin har bir o'yinchining faqat har 5-do'st o'yinida hisoblanadi (barcha do'stlar bo'yicha umumiy)."""
        self.c.execute("INSERT INTO results(game,players,winner,reason,mode,ts) VALUES(?,?,?,?,?,?)",
                       (game, json.dumps(seats, ensure_ascii=False), res.get("winner"), res.get("reason"), mode, int(time.time())))
        out = [None] * len(seats)
        if mode != "bot" and len(seats) == 2 and not any(p.get("bot") for p in seats):
            rows = [self._row(p["id"], game) for p in seats]
            w = res.get("winner")
            score = [0.5, 0.5] if w is None else [1.0, 0.0] if w == 0 else [0.0, 1.0]
            for i, me in enumerate(rows):
                before, opp = me["rating"], rows[1 - i]["rating"]
                me["played"] += 1
                me["wins" if score[i] == 1 else "losses" if score[i] == 0 else "draws"] += 1
                if mode == "friend":
                    me["friend_games"] += 1
                counted = mode != "friend" or me["friend_games"] % FRIEND_EVERY == 0
                exp = 1 / (1 + 10 ** ((opp - before) / 400))
                k = 40 if me["played"] <= 30 else 20
                me["new"] = max(100, round(before + k * (score[i] - exp))) if counted else before
                out[i] = {"before": before, "after": me["new"], "counted": counted,
                          "next": 0 if counted else FRIEND_EVERY - me["friend_games"] % FRIEND_EVERY}
            for me in rows:
                self.c.execute(
                    "INSERT INTO ratings VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(user_id,game) DO UPDATE SET rating=excluded.rating,"
                    "played=excluded.played,wins=excluded.wins,losses=excluded.losses,draws=excluded.draws,friend_games=excluded.friend_games",
                    (me["user_id"], game, me["new"], me["played"], me["wins"], me["losses"], me["draws"], me["friend_games"]))
        self.c.commit()
        return out
