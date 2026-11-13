import random, unittest

from server.games.durak.game import GAME, nxt

SPADE, HEART, DIAM, CLUB = 0, 1, 2, 3


def mk(hands, deck=(), trump=SPADE, att=0, t=None, phase="attack", limit=None, out=()):
    n = len(hands)
    s = {"n": n, "deck": [list(c) for c in deck], "trump": trump, "tc": [trump, 6], "hands": [[list(c) for c in h] for h in hands],
         "t": t or [], "att": att, "def": 0, "phase": phase, "limit": 6, "passed": [], "out": list(out), "disc": 0, "res": None, "prev": None}
    s["def"] = nxt(s, att)
    s["limit"] = limit or min(6, len(s["hands"][s["def"]]))
    return s


def acts(s):
    out = []
    for p in range(s["n"]):
        if p in s["out"]:
            continue
        me = GAME.view(s, p)["me"]
        out += [(p, {"play": c}) for c in me["canPlay"]]
        for k, ps in me["canDefend"].items():
            su, r = map(int, k.split("-"))
            out += [(p, {"defend": [su, r], "pair": i}) for i in ps]
        if me["canTake"]: out.append((p, {"take": True}))
        if me["canPass"]: out.append((p, {"pass": True}))
    return out


def ok(s, seat, m):
    GAME.apply(s, seat, m)


def bad(tc, s, seat, m):
    with tc.assertRaises(ValueError):
        GAME.apply(s, seat, m)


class Setup(unittest.TestCase):
    def test_new_deal(self):
        for n in range(2, 7):
            for _ in range(20):
                s = GAME.new(n)
                self.assertTrue(all(len(h) == 6 for h in s["hands"]))
                self.assertEqual(len(s["deck"]) + 6 * n, 36)
                low = [(c[1], p) for p, h in enumerate(s["hands"]) for c in h if c[0] == s["trump"]]
                if low: self.assertEqual(s["att"], min(low)[1])
                self.assertEqual(s["def"], (s["att"] + 1) % n)


class Round(unittest.TestCase):
    def base(self):
        return mk([[[1, 7], [2, 7], [3, 9]], [[1, 8], [1, 9], [3, 6]]], deck=[[2, 6], [2, 8], [3, 12], [3, 13]])

    def test_defended_round(self):
        s = self.base()
        bad(self, s, 1, {"play": [1, 8]})                      # hujumchi emas
        ok(s, 0, {"play": [1, 7]})
        self.assertEqual(s["phase"], "defend")
        bad(self, s, 0, {"play": [3, 9]})                      # daraja mos emas
        bad(self, s, 1, {"defend": [3, 6], "pair": 0})         # urmaydi
        bad(self, s, 0, {"defend": [1, 8], "pair": 0})         # himoyalanuvchi emas
        ok(s, 1, {"defend": [1, 8]})                           # pair ko'rsatilmasa yagona ochiq karta
        self.assertEqual(s["phase"], "attack")
        bad(self, s, 1, {"pass": True})                        # himoyalanuvchi bito demaydi
        ok(s, 0, {"pass": True})
        self.assertEqual((s["att"], s["def"], s["disc"], s["t"], s["phase"]), (1, 0, 2, [], "attack"))
        self.assertEqual(len(s["hands"][0]), 6)                # hujumchi 4 ta oldi
        self.assertFalse(s["prev"]["took"])
        self.assertEqual(s["limit"], 6)

    def test_take_with_throw_in(self):
        s = self.base()
        ok(s, 0, {"play": [1, 7]})
        bad(self, s, 0, {"take": True})
        ok(s, 1, {"take": True})
        self.assertEqual(s["phase"], "take")
        bad(self, s, 1, {"defend": [1, 8]})
        ok(s, 0, {"play": [2, 7]})                             # qo'shib tashlash; boshqa mos karta yo'q: raund o'zi tugaydi
        self.assertEqual((s["att"], s["def"], s["t"]), (0, 1, []))
        self.assertEqual(len(s["hands"][1]), 5)                # 3 + 2 olingan
        self.assertEqual(len(s["hands"][0]), 5)                # hujumchi qolgan 1 + 4 ta tortdi
        self.assertTrue(s["prev"]["took"])

    def test_limits_and_empty_pass(self):
        s = mk([[[1, 7], [2, 7], [3, 7]], [[1, 8], [1, 9], [3, 6]]], limit=1)
        bad(self, s, 0, {"pass": True})                        # stol bo'sh
        ok(s, 0, {"play": [1, 7]})
        bad(self, s, 0, {"play": [2, 7]})                      # limit
        bad(self, s, 0, {"play": [9, 9]}); bad(self, s, 0, {"bogus": 1}); bad(self, s, 1, {})

    def test_trump_beats_and_ranks(self):
        s = mk([[[1, 14], [2, 6]], [[0, 6], [1, 6], [2, 7]]], trump=SPADE)
        ok(s, 0, {"play": [1, 14]})
        bad(self, s, 1, {"defend": [1, 6], "pair": 0})
        ok(s, 1, {"defend": [0, 6], "pair": 0})                # kozir har qanday oddiy kartani uradi


class Multi(unittest.TestCase):
    def test_three_players_throw_in_and_refill_order(self):
        deck = [[2, 14], [2, 13], [2, 12], [2, 11], [2, 10], [3, 14], [3, 13], [3, 12], [3, 11], [3, 10], [3, 9], [3, 8]]
        s = mk([[[1, 7], [1, 9]], [[1, 8], [0, 6], [0, 9]], [[2, 7], [3, 7], [3, 6]]], deck=deck, att=0)
        ok(s, 0, {"play": [1, 7]})
        ok(s, 2, {"play": [2, 7]})                             # uchinchi o'yinchi ham qo'sha oladi
        bad(self, s, 1, {"play": [1, 8]})
        ok(s, 1, {"defend": [1, 8], "pair": 0})
        ok(s, 1, {"defend": [0, 6], "pair": 1})
        self.assertEqual(s["phase"], "attack")
        ok(s, 0, {"pass": True})                               # 0 da mos karta yo'q edi, lekin 2 da [3,7] bor
        self.assertEqual(s["phase"], "attack")                 # hali tugamadi: 2 kutilyapti
        self.assertEqual(GAME.turn(s), 2)
        ok(s, 2, {"pass": True})
        self.assertEqual((s["att"], s["def"], s["disc"]), (1, 2, 4))
        # tortish tartibi: hujumchi(0), keyin 2... [0, 2] dan keyin himoyalanuvchi(1) oxirida
        self.assertEqual([len(h) for h in s["hands"]], [6, 4, 6])      # zaxira 12 ta: 5 + 4 + qolgan 3
        self.assertEqual(s["hands"][0][-5:], [[3, 8], [3, 9], [3, 10], [3, 11], [3, 12]])
        self.assertEqual(s["hands"][2][-4:], [[3, 13], [3, 14], [2, 10], [2, 11]])
        self.assertEqual(s["hands"][1][-3:], [[2, 12], [2, 13], [2, 14]])

    def test_resign_multi(self):
        s = GAME.new(3)
        ok(s, 2, {"resign": True})
        self.assertEqual(s["res"], {"loser": 2, "winner": None, "reason": "resign"})
        bad(self, s, 0, {"pass": True})


class Ending(unittest.TestCase):
    def test_durak_two_players(self):
        s = mk([[[1, 7]], [[1, 8], [2, 9]]])
        ok(s, 0, {"play": [1, 7]}); ok(s, 1, {"defend": [1, 8]})
        self.assertEqual(s["res"], {"loser": 1, "winner": 0, "reason": "durak"})
        self.assertEqual(s["out"], [0])
        self.assertIsNone(GAME.turn(s)); self.assertEqual(GAME.result(s)["winner"], 0)

    def test_take_then_durak(self):
        s = mk([[[1, 7]], [[3, 8], [2, 9]]])
        ok(s, 0, {"play": [1, 7]}); ok(s, 1, {"take": True})
        self.assertEqual(s["res"]["loser"], 1)

    def test_draw_when_both_empty(self):
        s = mk([[[1, 7]], [[1, 8]]])
        ok(s, 0, {"play": [1, 7]}); ok(s, 1, {"defend": [1, 8]})
        self.assertEqual(s["res"], {"loser": None, "winner": None, "reason": "draw"})

    def test_three_players_one_out_game_continues(self):
        s = mk([[[1, 7]], [[1, 8], [2, 9]], [[2, 7], [3, 7]]])
        ok(s, 0, {"play": [1, 7]}); ok(s, 1, {"defend": [1, 8]}); ok(s, 2, {"pass": True}) if s["phase"] == "attack" else None
        self.assertIsNone(s["res"]); self.assertEqual(s["out"], [0])
        self.assertEqual((s["att"], s["def"]), (1, 2))


class View(unittest.TestCase):
    def test_privacy_and_options(self):
        s = mk([[[1, 7], [2, 7]], [[1, 8], [0, 6], [3, 9]]], t=[[[1, 7], None]], phase="defend", att=0)
        s["hands"][0] = [[2, 7]]
        v0, v1 = GAME.view(s, 0), GAME.view(s, 1)
        self.assertNotIn("hands", v0)
        self.assertEqual(v0["hand"], [[2, 7]]); self.assertEqual(v0["counts"], [1, 3])
        self.assertEqual(v0["me"]["canPlay"], [[2, 7]]); self.assertFalse(v0["me"]["canTake"])
        self.assertEqual(v1["me"]["canDefend"], {"1-8": [0], "0-6": [0]})
        self.assertTrue(v1["me"]["canTake"]); self.assertEqual(v1["me"]["canPlay"], [])
        import json; json.dumps(v0); json.dumps(v1)


class Fuzz(unittest.TestCase):
    def invariants(self, s):
        cards = [tuple(c) for c in s["deck"]] + [tuple(c) for h in s["hands"] for c in h] + \
                [tuple(c) for p in s["t"] for c in p if c]
        self.assertEqual(len(cards) + s["disc"], 36)
        self.assertEqual(len(set(cards)), len(cards))

    def test_random_legal_play_never_deadlocks(self):
        random.seed(7)
        for n in range(2, 7):
            for _ in range(40):
                s = GAME.new(n)
                for step in range(4000):
                    if s["res"]: break
                    a = acts(s)
                    self.assertTrue(a, f"qotib qoldi n={n}: {s}")
                    self.assertIn(GAME.turn(s), {x[0] for x in a})
                    seat, m = random.choice(a)
                    GAME.apply(s, seat, m)
                    self.invariants(s)
                self.assertTrue(s["res"], "o'yin tugamadi")

    def test_bots_finish_games(self):
        for n in (2, 3, 4):
            for _ in range(30):
                s = GAME.new(n)
                for step in range(4000):
                    if s["res"]: break
                    t = GAME.turn(s)
                    GAME.apply(s, t, GAME.bot_move(s, t))
                self.assertTrue(s["res"])


class Integration(unittest.TestCase):
    def test_hub_bot_and_friend_rooms(self):
        from server.registry import Registry
        from server.rooms import Hub
        reg = Registry(); reg.load()
        self.assertIn("durak", reg.games)
        h = Hub(reg); u = {"id": 1, "name": "Ali"}
        rid = h.bot(u, "durak")[0][1]["id"]
        for _ in range(3000):
            while h.needs_bot(rid): h.bot_step(rid)
            r = h.rooms[rid]
            if r.status == "over": break
            me = r.seats.index(next(p for p in r.seats if p["id"] == 1))
            options = acts(r.state)
            mine = [m for p, m in options if p == me]
            self.assertTrue(mine)
            out = h.move(u, random.choice(mine))
            self.assertNotEqual(out[0][1]["t"], "err", out)
        self.assertEqual(h.rooms[rid].status, "over")
        # 3 kishilik do'stlar xonasi
        h = Hub(reg); a, b, c = ({"id": i, "name": f"U{i}"} for i in (1, 2, 3))
        code = h.create(a, "durak")[0][1]["code"]
        h.join(b, code); self.assertEqual(h.start(c)[0][1]["t"], "err")
        h.join(c, code)
        out = h.start(a)
        self.assertEqual({m["status"] for _, m in out}, {"playing"})
        self.assertTrue(all(len(m["view"]["hand"]) == 6 for _, m in out))


if __name__ == "__main__":
    unittest.main()
