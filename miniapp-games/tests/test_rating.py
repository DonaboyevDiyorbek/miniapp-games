import unittest

from server.db import DB
from server.registry import Registry
from server.rooms import Hub

A, B, C = {"id": 1, "name": "Ali"}, {"id": 2, "name": "Vali"}, {"id": 3, "name": "Sami"}


def seats(a=1, b=2, bot=False):
    return [{"id": a, "name": "A", "bot": False}, {"id": b, "name": "B", "bot": bot}]


class Elo(unittest.TestCase):
    def test_equal_players_win_loss_draw(self):
        db = DB()
        out = db.record("shaxmat", seats(), {"winner": 0}, "queue")
        self.assertEqual((out[0]["before"], out[0]["after"], out[1]["after"]), (1000, 1020, 980))   # K=40
        self.assertEqual(db.profile(1, "shaxmat"), {"rating": 1020, "rank": 1})
        self.assertEqual(db.profile(2, "shaxmat")["rank"], 2)
        out = db.record("shaxmat", seats(), {"winner": None}, "queue")           # 1020 vs 980, durang
        self.assertLess(out[0]["after"], 1020); self.assertGreater(out[1]["after"], 980)

    def test_bot_games_never_rated(self):
        db = DB()
        self.assertEqual(db.record("shaxmat", seats(bot=True), {"winner": 0}, "bot"), [None, None])
        self.assertEqual(db.profile(1, "shaxmat"), {"rating": 1000, "rank": None})
        self.assertEqual(db.leaderboard("shaxmat"), [])

    def test_friend_games_count_every_fifth(self):
        db = DB()
        for i in range(1, 6):
            out = db.record("shaxmat", seats(), {"winner": 0}, "friend")
            self.assertEqual(out[0]["counted"], i == 5, i)
            self.assertEqual(out[0]["next"], 0 if i == 5 else 5 - i)
            if i < 5:
                self.assertEqual(db.profile(1, "shaxmat")["rating"], 1000)
        self.assertGreater(db.profile(1, "shaxmat")["rating"], 1000)
        self.assertLess(db.profile(2, "shaxmat")["rating"], 1000)

    def test_friend_counter_is_overall_not_per_pair(self):
        db = DB()
        for opp in (2, 3, 4, 5):
            db.record("shaxmat", seats(1, opp), {"winner": 0}, "friend")
        self.assertEqual(db.profile(1, "shaxmat")["rating"], 1000)
        out = db.record("shaxmat", seats(1, 6), {"winner": 0}, "friend")           # 1 ning 5-do'st o'yini (boshqa do'st bilan)
        self.assertTrue(out[0]["counted"]); self.assertFalse(out[1]["counted"])    # 6 uchun bu faqat 1-o'yin
        self.assertGreater(db.profile(1, "shaxmat")["rating"], 1000)
        self.assertEqual(db.profile(6, "shaxmat")["rating"], 1000)

    def test_floor_and_leaderboard_limit_order(self):
        db = DB()
        for uid in range(10, 16): db.upsert_user(uid, f"U{uid}")
        for uid in range(11, 16): db.record("shaxmat", seats(10, uid), {"winner": 1}, "queue")
        top = db.leaderboard("shaxmat", 3)
        self.assertEqual(len(top), 3)
        self.assertEqual([r["rank"] for r in top], [1, 2, 3])
        self.assertTrue(all(top[i]["rating"] >= top[i + 1]["rating"] for i in range(2)))
        self.assertGreaterEqual(db.profile(10, "shaxmat")["rating"], 100)
        self.assertEqual(db.profile(10, "shaxmat")["rank"], len(db.leaderboard("shaxmat")))   # eng oxirgi

    def test_ratings_are_per_game(self):
        db = DB()
        db.record("shaxmat", seats(), {"winner": 0}, "queue")
        self.assertEqual(db.profile(1, "xo")["rating"], 1000)


class HubRating(unittest.TestCase):
    def mk(self):
        reg = Registry(); reg.load()
        db = DB()
        for u in (A, B, C): db.upsert_user(u["id"], u["name"])
        return Hub(reg, record=db.record, profile=db.profile), db

    def test_queue_game_rates_and_reports(self):
        h, db = self.mk()
        h.queue(A, "shaxmat"); out = dict(h.queue(B, "shaxmat"))
        self.assertTrue(all("rating" in s for s in out[1]["seats"]))
        r = list(h.rooms.values())[0]
        loser = r.seats[1]["id"]
        o = dict(h.leave({"id": loser, "name": "x"}))
        winner_msg = [m for u, m in o.items() if u != loser][0]
        self.assertEqual(winner_msg["result"]["reason"], "leave")
        self.assertEqual(winner_msg["result"]["rating"][0]["after"] > 1000, True)
        self.assertEqual(db.profile(r.seats[0]["id"], "shaxmat")["rank"], 1)

    def test_bot_and_friend_modes(self):
        h, db = self.mk()
        rid = h.bot(A, "shaxmat")[0][1]["id"]
        self.assertEqual(h.rooms[rid].mode, "bot")
        h.leave(A)
        self.assertEqual(db.leaderboard("shaxmat"), [])
        code = h.create(A, "shaxmat")[0][1]["code"]
        h.join(B, code)
        self.assertEqual(list(h.rooms.values())[0].mode, "friend")
        h.leave(A)
        self.assertEqual(db.profile(2, "shaxmat")["rating"], 1000)       # 1-do'st o'yin: hisoblanmadi
        self.assertIsNotNone(db.profile(2, "shaxmat")["rank"])           # lekin o'ynagan sifatida ro'yxatda


if __name__ == "__main__":
    unittest.main()
