import hashlib, hmac, io, json, shutil, tempfile, time, unittest, zipfile
from pathlib import Path
from urllib.parse import urlencode

from server import auth
from server.db import DB
from server.registry import GAMES_DIR, Registry
from server.rooms import Hub

A, B, C = {"id": 1, "name": "Ali"}, {"id": 2, "name": "Vali"}, {"id": 3, "name": "Sami"}


def mk():
    reg = Registry(); reg.load()
    return Hub(reg), reg


def init_data(token, uid=7, age=0, bad=False):
    d = {"auth_date": str(int(time.time()) - age), "user": json.dumps({"id": uid, "first_name": "Ali"})}
    chk = "\n".join(f"{k}={d[k]}" for k in sorted(d))
    sec = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    d["hash"] = hmac.new(sec, chk.encode(), hashlib.sha256).hexdigest()
    if bad:
        d["hash"] = "0" * 64
    return urlencode(d)


class Auth(unittest.TestCase):
    def test_ok_bad_old(self):
        self.assertEqual(auth.validate(init_data("t:1"), "t:1")["id"], 7)
        self.assertIsNone(auth.validate(init_data("t:1", bad=True), "t:1"))
        self.assertIsNone(auth.validate(init_data("t:1"), "other"))
        self.assertIsNone(auth.validate(init_data("t:1", age=10**6), "t:1"))
        self.assertIsNone(auth.validate("", "t:1"))


class XO(unittest.TestCase):
    def test_bot_never_illegal_and_game_ends(self):
        from server.games.xo.game import GAME
        for _ in range(200):
            s = GAME.new(2)
            while not GAME.result(s):
                GAME.apply(s, s["turn"], GAME.bot_move(s, s["turn"]))
        s = GAME.new(2)
        with self.assertRaises(ValueError): GAME.apply(s, 1, {"cell": 0})
        GAME.apply(s, 0, {"cell": 0})
        with self.assertRaises(ValueError): GAME.apply(s, 1, {"cell": 0})
        with self.assertRaises(ValueError): GAME.apply(s, 1, {"cell": "x"})

    def test_win(self):
        from server.games.xo.game import GAME
        s = GAME.new(2)
        for seat, c in [(0, 0), (1, 3), (0, 1), (1, 4), (0, 2)]: GAME.apply(s, seat, {"cell": c})
        self.assertEqual(GAME.result(s)["winner"], 0)


class HubT(unittest.TestCase):
    def test_matchmaking(self):
        h, _ = mk()
        self.assertEqual(h.queue(A, "xo")[0][1]["t"], "queued")
        out = h.queue(B, "xo")
        self.assertEqual({u for u, _ in out}, {1, 2})
        self.assertTrue(all(m["status"] == "playing" for _, m in out))
        self.assertEqual(h.queue(A, "xo")[0][1]["t"], "err")   # allaqachon o'yinda

    def test_private_room_and_moves(self):
        h, _ = mk()
        code = h.create(A, "xo")[0][1]["code"]
        self.assertEqual(h.join(B, "zzzzz")[0][1]["t"], "err")
        out = dict(h.join(B, code.lower()))
        self.assertEqual(out[1]["status"], "playing")
        turn_uid = {1: A, 2: B}[[u for u, m in out.items() if m["turn"] == m["you"]][0]]
        other = B if turn_uid is A else A
        self.assertEqual(h.move(other, {"cell": 0})[0][1]["t"], "err")
        r = dict(h.move(turn_uid, {"cell": 0}))
        self.assertEqual(r[other["id"]]["view"]["b"][0] in (0, 1), True)

    def test_bot_game_runs_to_end(self):
        h, _ = mk()
        out = h.bot(A, "xo")
        rid = out[0][1]["id"]
        for _ in range(30):
            if h.needs_bot(rid): h.bot_step(rid); continue
            r = h.rooms[rid]
            if r.status == "over": break
            h.move(A, {"cell": r.state["b"].index(None)})
        self.assertEqual(h.rooms[rid].status, "over")

    def test_leave_forfeit_and_cleanup(self):
        h, _ = mk()
        h.queue(A, "xo"); h.queue(B, "xo")
        out = dict(h.leave(A))
        self.assertEqual(out[2]["result"], {"winner": out[2]["you"], "reason": "leave", "left": 1 - out[2]["you"]})
        h.leave(B)
        self.assertFalse(h.rooms)
        self.assertFalse(h.user_room)

    def test_host_closes_waiting_room(self):
        h, _ = mk()
        code = h.create(A, "xo")[0][1]["code"]
        h.leave(A)
        self.assertEqual(h.join(B, code)[0][1]["t"], "err")

    def test_reap_timeout(self):
        h, _ = mk()
        h.queue(A, "xo"); h.queue(B, "xo")
        out = h.reap(now=time.time() + 5000, idle=900)
        self.assertTrue(out and out[0][1]["result"]["reason"] == "timeout")

    def test_disabled_game_and_reconnect(self):
        h, reg = mk()
        h.allowed = lambda gid: False
        self.assertEqual(h.queue(A, "xo")[0][1]["t"], "err")
        h.allowed = lambda gid: True
        h.queue(A, "xo"); h.queue(B, "xo")
        self.assertEqual(h.enter(A)[0][1]["t"], "room")


class Plug(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        shutil.copytree(GAMES_DIR / "xo", self.d / "xo")
        self.reg = Registry(self.d); self.reg.load()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def zipf(self, files):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            for n, c in files.items(): z.writestr(n, c)
        return b.getvalue()

    def test_install_ok_nested_and_flat(self):
        game = (GAMES_DIR / "xo" / "game.py").read_text()
        for pre, gid in (("", "demo"), ("demo2/", "demo2")):
            man = json.dumps({"id": gid, "name": "Demo"})
            data = self.zipf({pre + "manifest.json": man, pre + "game.py": game, pre + "client.js": "//"})
            self.assertEqual(self.reg.install_zip(data), gid)
            self.assertIn(gid, self.reg.games)
        with self.assertRaises(ValueError): self.reg.install_zip(data)   # dublikat

    def test_install_rejects(self):
        man = json.dumps({"id": "evil"})
        bad = [b"not a zip",
               self.zipf({"manifest.json": man, "game.py": "GAME=1", "client.js": "//"}),            # GAME noto'g'ri
               self.zipf({"manifest.json": man, "game.py": "x=", "client.js": "//"}),                 # sintaksis xato
               self.zipf({"manifest.json": man, "../game.py": "", "client.js": "//"}),                # zip-slip
               self.zipf({"manifest.json": json.dumps({"id": "../x"}), "game.py": "", "client.js": ""})]
        for b in bad:
            with self.assertRaises(ValueError): self.reg.install_zip(b)
        self.assertFalse((self.d / "evil").exists())
        self.assertEqual(sorted(p.name for p in self.d.iterdir()), ["xo"])


class DBT(unittest.TestCase):
    def test_catalog(self):
        db = DB(); db.sync_games({"xo": {"name": "XO", "icon": "x"}, "chess": {"name": "Chess"}})
        db.update_game("xo", enabled=0, title="Bad", evil="x")
        self.assertEqual([g["id"] for g in db.catalog()], ["chess"])
        self.assertFalse(db.is_enabled("xo"))
        db.sync_games({"xo": {"name": "Other"}})
        self.assertEqual({g["id"]: g["title"] for g in db.catalog(False)}["xo"], "Bad")   # admin o'zgarishi saqlanadi


if __name__ == "__main__":
    unittest.main()
