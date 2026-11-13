"""Durak (podkidnoy): 36 karta, 2–6 o'yinchi. Karta = [mast 0..3, daraja 6..14] (11=J, 12=Q, 13=K, 14=A).
Hujumchi boshlaydi; himoyalanuvchidan boshqa har bir o'yinchi daraja mos kelsa karta qo'sha oladi (podkidnoy).
Yurishlar: {"play":karta} | {"defend":karta,"pair":i} | {"take":true} | {"pass":true} | {"resign":true}."""
import random

from server.games.base import Game

HAND = 6


def cost(s, c):
    return c[1] + (100 if c[0] == s["trump"] else 0)


def beats(s, d, a):
    return (d[0] == a[0] and d[1] > a[1]) or (d[0] == s["trump"] and a[0] != s["trump"])


def active(s):
    return [i for i in range(s["n"]) if i not in s["out"]]


def nxt(s, i):
    for k in range(1, s["n"] + 1):
        j = (i + k) % s["n"]
        if j not in s["out"]:
            return j
    return i


def after(s, a):
    """a dan keyingi faol o'yinchilar (soat strelkasi bo'yicha), a o'zi kiritilmaydi."""
    return [(a + k) % s["n"] for k in range(1, s["n"]) if (a + k) % s["n"] not in s["out"]]


def open_idx(s):
    return [i for i, p in enumerate(s["t"]) if p[1] is None]


def table_ranks(s):
    return {c[1] for p in s["t"] for c in p if c}


def can_add(s, seat, c):
    if s["res"] or seat in s["out"] or seat == s["def"] or len(s["t"]) >= s["limit"]:
        return False
    if not s["t"]:
        return seat == s["att"]
    return c[1] in table_ranks(s)


def addable(s, seat):
    return any(can_add(s, seat, c) for c in s["hands"][seat])


def sync(s):
    if s["phase"] != "take":
        s["phase"] = "defend" if open_idx(s) else "attack"


def finish(s, took):
    a, d = s["att"], s["def"]
    cards = [c for p in s["t"] for c in p if c]
    s["prev"] = {"t": s["t"], "took": took, "def": d}
    if took:
        s["hands"][d].extend(cards)
    else:
        s["disc"] += len(cards)
    for p in [a] + [x for x in after(s, a) if x != d] + [d]:      # avval hujumchi, oxirida himoyalanuvchi
        while len(s["hands"][p]) < HAND and s["deck"]:
            s["hands"][p].append(s["deck"].pop())
    if not s["deck"]:
        for p in active(s):
            if not s["hands"][p]:
                s["out"].append(p)
    act = active(s)
    s["t"], s["passed"], s["phase"] = [], [], "attack"
    if len(act) <= 1:
        loser = act[0] if act else None
        two = s["n"] == 2 and loser is not None
        s["res"] = {"loser": loser, "winner": (1 - loser) if two else None, "reason": "durak" if loser is not None else "draw"}
        return
    na = nxt(s, d) if took or d not in act else d
    s["att"], s["def"] = na, nxt(s, na)
    s["limit"] = min(HAND, len(s["hands"][s["def"]]))


def maybe_end(s):
    if s["phase"] == "defend" or not s["t"]:
        return
    d = s["def"]
    if s["phase"] == "attack" and not s["hands"][d]:
        return finish(s, False)
    for p in active(s):
        if p != d and p not in s["passed"] and addable(s, p):
            return
    finish(s, s["phase"] == "take")


def pick(s, seat, v):
    if not (isinstance(v, list) and len(v) == 2 and all(type(x) is int for x in v)) or v not in s["hands"][seat]:
        raise ValueError("Sizda bunday karta yo'q")
    return v


class Durak(Game):
    min_players, max_players = 2, 6

    def new(self, n, options=None):
        deck = [[m, r] for m in range(4) for r in range(6, 15)]
        random.shuffle(deck)
        s = {"n": n, "deck": deck, "trump": deck[0][0], "tc": list(deck[0]), "hands": [[] for _ in range(n)], "t": [],
             "att": 0, "def": 1, "phase": "attack", "limit": HAND, "passed": [], "out": [], "disc": 0, "res": None, "prev": None}
        for _ in range(HAND):
            for p in range(n):
                s["hands"][p].append(deck.pop())
        low = [(c[1], p) for p, h in enumerate(s["hands"]) for c in h if c[0] == s["trump"]]
        s["att"] = min(low)[1] if low else 0
        s["def"] = nxt(s, s["att"])
        s["limit"] = min(HAND, len(s["hands"][s["def"]]))
        return s

    def turn(self, s):
        if s["res"]:
            return None
        if s["phase"] == "defend":
            return s["def"]
        if s["t"]:
            for p in [s["att"]] + after(s, s["att"]):
                if p != s["def"] and p not in s["passed"] and addable(s, p):
                    return p
        return s["att"]

    def result(self, s):
        return s["res"]

    def apply(self, s, seat, m):
        if s["res"]:
            raise ValueError("O'yin tugagan")
        if m.get("resign"):
            s["res"] = {"loser": seat, "winner": (1 - seat) if s["n"] == 2 else None, "reason": "resign"}
            return
        if seat in s["out"]:
            raise ValueError("Siz o'yindan chiqqansiz")
        d = s["def"]
        if "play" in m:
            c = pick(s, seat, m["play"])
            if not can_add(s, seat, c):
                raise ValueError("Bu kartani tashlab bo'lmaydi")
            s["hands"][seat].remove(c)
            s["t"].append([c, None])
            s["passed"] = []
            sync(s)
        elif "defend" in m:
            if seat != d or s["phase"] != "defend":
                raise ValueError("Hozir himoyalana olmaysiz")
            c = pick(s, seat, m["defend"])
            i = m.get("pair")
            if i is None and len(open_idx(s)) == 1:
                i = open_idx(s)[0]
            if type(i) is not int or i not in open_idx(s):
                raise ValueError("Qaysi kartani urishni tanlang")
            if not beats(s, c, s["t"][i][0]):
                raise ValueError("Bu karta urmaydi")
            s["hands"][seat].remove(c)
            s["t"][i][1] = c
            s["passed"] = []
            sync(s)
        elif m.get("take"):
            if seat != d or s["phase"] != "defend":
                raise ValueError("Hozir olib bo'lmaydi")
            s["phase"], s["passed"] = "take", []
        elif m.get("pass"):
            if seat == d or not s["t"] or s["phase"] == "defend" or seat in s["passed"]:
                raise ValueError("Hozir «bito» deb bo'lmaydi")
            s["passed"].append(seat)
        else:
            raise ValueError("Noma'lum yurish")
        maybe_end(s)

    def view(self, s, seat):
        me = {"canPlay": [], "canDefend": {}, "canTake": False, "canPass": False}
        hand = s["hands"][seat]
        if not s["res"] and seat not in s["out"]:
            me["canPlay"] = [c for c in hand if can_add(s, seat, c)]
            if seat == s["def"] and s["phase"] == "defend":
                for c in hand:
                    ps = [i for i in open_idx(s) if beats(s, c, s["t"][i][0])]
                    if ps:
                        me["canDefend"][f"{c[0]}-{c[1]}"] = ps
                me["canTake"] = True
            me["canPass"] = seat != s["def"] and bool(s["t"]) and s["phase"] != "defend" and seat not in s["passed"]
        return {"n": s["n"], "trump": s["trump"], "tc": s["tc"] if s["deck"] else None, "deck": len(s["deck"]),
                "disc": s["disc"], "t": s["t"], "att": s["att"], "def": s["def"], "phase": s["phase"], "limit": s["limit"],
                "out": s["out"], "counts": [len(h) for h in s["hands"]], "hand": hand, "prev": s["prev"], "res": s["res"], "me": me}

    def bot_move(self, s, seat):
        h = s["hands"][seat]
        if s["phase"] == "defend":
            i = open_idx(s)[0]
            a = s["t"][i][0]
            c = sorted((x for x in h if beats(s, x, a)), key=lambda x: cost(s, x))
            waste = c and c[0][0] == s["trump"] and a[0] != s["trump"] and len(s["deck"]) > 5 and c[0][1] >= 12 and a[1] <= 9
            return {"take": True} if not c or waste else {"defend": c[0], "pair": i}
        cands = sorted((x for x in h if can_add(s, seat, x)), key=lambda x: cost(s, x))
        if cands and (not s["t"] or cands[0][0] != s["trump"] or not s["deck"]):
            return {"play": cands[0]}
        return {"pass": True}


GAME = Durak()
