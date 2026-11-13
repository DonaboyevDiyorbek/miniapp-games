import copy, unittest

from server.games.shaxmat.game import GAME, advance, judge, legal

FILES = "abcdefgh"


def sq(name):
    return (8 - int(name[1])) * 8 + FILES.index(name[0])


def from_fen(fen):
    parts = fen.split()
    b = []
    for ch in parts[0].replace("/", ""):
        b += [""] * int(ch) if ch.isdigit() else [ch]
    ep = -1 if len(parts) < 4 or parts[3] == "-" else sq(parts[3])
    return {"b": b, "turn": 0 if parts[1] == "w" else 1, "castle": "" if parts[2] == "-" else parts[2], "ep": ep,
            "half": 0, "full": 1, "last": None, "res": None, "rep": {}}


def perft(s, d):
    lg = legal(s, s["turn"])
    return len(lg) if d == 1 else sum(perft(advance(s, m), d - 1) for m in lg)


def play(s, seat, frm, to, promo=""):
    GAME.apply(s, seat, {"from": sq(frm), "to": sq(to), "promo": promo})


START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"
KIWI = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -"
P3 = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -"
P4 = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
P5 = "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"


class Perft(unittest.TestCase):
    """Taniqli perft qiymatlari: qoidalar (rokirovka, en passant, almashtirish, shoh himoyasi) to'g'riligini isbotlaydi."""

    def test_start(self):
        self.assertEqual([perft(from_fen(START), d) for d in (1, 2, 3, 4)], [20, 400, 8902, 197281])

    def test_kiwipete(self):
        self.assertEqual([perft(from_fen(KIWI), d) for d in (1, 2, 3)], [48, 2039, 97862])

    def test_position3(self):
        self.assertEqual([perft(from_fen(P3), d) for d in (1, 2, 3, 4)], [14, 191, 2812, 43238])

    def test_position4(self):
        self.assertEqual([perft(from_fen(P4), d) for d in (1, 2, 3)], [6, 264, 9467])

    def test_position5(self):
        self.assertEqual([perft(from_fen(P5), d) for d in (1, 2, 3)], [44, 1486, 62379])


class Flow(unittest.TestCase):
    def test_fools_mate(self):
        s = GAME.new(2)
        for seat, a, b in [(0, "f2", "f3"), (1, "e7", "e5"), (0, "g2", "g4"), (1, "d8", "h4")]:
            play(s, seat, a, b)
        self.assertEqual(GAME.result(s), {"winner": 1, "reason": "mate"})
        self.assertIsNone(GAME.turn(s))
        with self.assertRaises(ValueError): play(s, 0, "a2", "a3")

    def test_illegal_and_wrong_turn(self):
        s = GAME.new(2)
        with self.assertRaises(ValueError): play(s, 1, "e7", "e5")
        with self.assertRaises(ValueError): play(s, 0, "e2", "e5")
        with self.assertRaises(ValueError): GAME.apply(s, 0, {"from": "a", "to": 1})
        with self.assertRaises(ValueError): GAME.apply(s, 0, {})

    def test_check_rules(self):
        s = from_fen("4k3/8/8/8/8/8/4r3/4K3 w - -")   # shoh yonidagi himoyasiz rux: d1, f1 yoki rux olinadi
        self.assertEqual(sorted(m[1] for m in legal(s, 0)), sorted([sq("d1"), sq("f1"), sq("e2")]))
        s = from_fen("4k3/4r3/8/8/8/8/4B3/4K3 w - -")   # e2 fil bog'langan
        self.assertEqual([m for m in legal(s, 0) if m[0] == sq("e2")], [])

    def test_stalemate_and_material(self):
        self.assertEqual(judge(from_fen("7k/5Q2/6K1/8/8/8/8/8 b - -"))["res"], {"winner": None, "reason": "stalemate"})
        self.assertEqual(judge(from_fen("8/8/4k3/8/8/3NK3/8/8 w - -"))["res"]["reason"], "material")
        self.assertIsNone(judge(from_fen("8/8/4k3/8/8/3NK3/8/7R w - -"))["res"])

    def test_promotion_default_queen_and_choice(self):
        s = from_fen("8/P6k/8/8/8/8/8/K7 w - -")
        c = copy.deepcopy(s); play(c, 0, "a7", "a8")
        self.assertEqual(c["b"][sq("a8")], "Q")
        c = copy.deepcopy(s); play(c, 0, "a7", "a8", "n")
        self.assertEqual(c["b"][sq("a8")], "N")

    def test_en_passant_and_castling(self):
        s = from_fen("4k3/8/8/8/3p4/8/4P3/4K3 w - -")
        play(s, 0, "e2", "e4"); play(s, 1, "d4", "e3")
        self.assertEqual(s["b"][sq("e4")], "")
        s = from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq -")
        play(s, 0, "e1", "g1")
        self.assertEqual((s["b"][sq("g1")], s["b"][sq("f1")], s["castle"]), ("K", "R", "kq"))
        play(s, 1, "e8", "c8")
        self.assertEqual((s["b"][sq("c8")], s["b"][sq("d8")], s["castle"]), ("k", "r", ""))

    def test_repetition_and_resign(self):
        s = GAME.new(2)
        for _ in range(2):
            for seat, a, b in [(0, "g1", "f3"), (1, "g8", "f6"), (0, "f3", "g1"), (1, "f6", "g8")]:
                play(s, seat, a, b)
        self.assertEqual(GAME.result(s), {"winner": None, "reason": "repetition"})
        s = GAME.new(2); GAME.apply(s, 1, {"resign": True})
        self.assertEqual(GAME.result(s), {"winner": 0, "reason": "resign"})

    def test_view(self):
        s = GAME.new(2)
        v = GAME.view(s, 0)
        self.assertEqual(sum(len(x) for x in v["moves"].values()), 20)
        self.assertNotIn("moves", GAME.view(s, 1))
        self.assertEqual(v["check"], -1)

    def test_bot_plays_legal_full_games(self):
        for _ in range(3):
            s = GAME.new(2)
            for ply in range(300):
                if GAME.result(s): break
                GAME.apply(s, s["turn"], GAME.bot_move(s, s["turn"]))
            self.assertTrue(ply > 5)

    def test_bot_mate_in_one_and_free_queen(self):
        s = from_fen("6k1/5ppp/8/8/8/8/8/R3K3 w - -")
        GAME.apply(s, 0, GAME.bot_move(s, 0))
        self.assertEqual(GAME.result(s), {"winner": 0, "reason": "mate"})
        s = from_fen("4k3/8/8/3q4/8/8/8/3RK3 w - -")
        m = GAME.bot_move(s, 0)
        self.assertEqual((m["from"], m["to"]), (sq("d1"), sq("d5")))


if __name__ == "__main__":
    unittest.main()
