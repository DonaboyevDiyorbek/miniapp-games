"""Shaxmat: rokirovka, en passant, piyodani almashtirish, mat/pat, 50 yurish va 3 marta takrorlanish.
Katak raqami 0..63: 0 = a8, 7 = h8, 56 = a1, 63 = h1. Oq = seat 0 (bosh harf), qora = seat 1 (kichik harf)."""
import random

from server.games.base import Game

START = list("rnbqkbnr") + ["p"] * 8 + [""] * 32 + ["P"] * 8 + list("RNBQKBNR")
KNIGHT = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))
KING = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
ROOK, BISH = ((-1, 0), (1, 0), (0, -1), (0, 1)), ((-1, -1), (-1, 1), (1, -1), (1, 1))
CORNER = {63: "K", 56: "Q", 7: "k", 0: "q"}
VAL = {"p": 100, "n": 320, "b": 330, "r": 500, "q": 900, "k": 0}
DEPTH = 2


def attacked(b, sq, by):
    """sq katagi `by` (0 oq, 1 qora) donalari hujumi ostidami."""
    r, c = divmod(sq, 8)
    f = str.upper if by == 0 else str.lower
    pr = r + 1 if by == 0 else r - 1
    if 0 <= pr < 8:
        for dc in (-1, 1):
            if 0 <= c + dc < 8 and b[pr * 8 + c + dc] == f("p"):
                return True
    for dirs, ch in ((KNIGHT, f("n")), (KING, f("k"))):
        for dr, dc in dirs:
            rr, cc = r + dr, c + dc
            if 0 <= rr < 8 and 0 <= cc < 8 and b[rr * 8 + cc] == ch:
                return True
    for dirs, kinds in ((ROOK, (f("r"), f("q"))), (BISH, (f("b"), f("q")))):
        for dr, dc in dirs:
            rr, cc = r + dr, c + dc
            while 0 <= rr < 8 and 0 <= cc < 8:
                p = b[rr * 8 + cc]
                if p:
                    if p in kinds:
                        return True
                    break
                rr += dr
                cc += dc
    return False


def pseudo(s, seat):
    b, out = s["b"], []
    mine = str.isupper if seat == 0 else str.islower
    for sq, p in enumerate(b):
        if not p or not mine(p):
            continue
        r, c = divmod(sq, 8)
        k = p.lower()
        if k == "p":
            d = -1 if seat == 0 else 1
            start, last = (6, 0) if seat == 0 else (1, 7)

            def add(t):
                if t // 8 == last:
                    out.extend((sq, t, x) for x in "qrbn")
                else:
                    out.append((sq, t, ""))
            if 0 <= r + d < 8:
                one = sq + d * 8
                if not b[one]:
                    add(one)
                    if r == start and not b[one + d * 8]:
                        out.append((sq, one + d * 8, ""))
                for dc in (-1, 1):
                    if 0 <= c + dc < 8:
                        t = one + dc
                        if (b[t] and not mine(b[t])) or t == s["ep"]:
                            add(t)
        elif k in "nk":
            for dr, dc in (KNIGHT if k == "n" else KING):
                rr, cc = r + dr, c + dc
                if 0 <= rr < 8 and 0 <= cc < 8:
                    t = rr * 8 + cc
                    if not b[t] or not mine(b[t]):
                        out.append((sq, t, ""))
            if k == "k" and sq == (60 if seat == 0 else 4):
                ks, qs, rk = ("K", "Q", "R") if seat == 0 else ("k", "q", "r")
                cs = s["castle"]
                if (ks in cs or qs in cs) and not attacked(b, sq, 1 - seat):
                    if ks in cs and not b[sq + 1] and not b[sq + 2] and b[sq + 3] == rk and not attacked(b, sq + 1, 1 - seat):
                        out.append((sq, sq + 2, ""))
                    if qs in cs and not b[sq - 1] and not b[sq - 2] and not b[sq - 3] and b[sq - 4] == rk \
                            and not attacked(b, sq - 1, 1 - seat):
                        out.append((sq, sq - 2, ""))
        else:
            for dr, dc in (ROOK if k == "r" else BISH if k == "b" else ROOK + BISH):
                rr, cc = r + dr, c + dc
                while 0 <= rr < 8 and 0 <= cc < 8:
                    t = rr * 8 + cc
                    if not b[t]:
                        out.append((sq, t, ""))
                    else:
                        if not mine(b[t]):
                            out.append((sq, t, ""))
                        break
                    rr += dr
                    cc += dc
    return out


def do(b, fr, to, promo, ep):
    """Yurishni taxtaga qo'llaydi (en passant, rokirovka, almashtirish bilan)."""
    p = b[fr]
    if p.lower() == "p" and to == ep and not b[to] and fr % 8 != to % 8:
        b[to + (8 if p == "P" else -8)] = ""
    if p.lower() == "k" and abs(to - fr) == 2:
        if to > fr:
            b[fr + 1], b[fr + 3] = b[fr + 3], ""
        else:
            b[fr - 1], b[fr - 4] = b[fr - 4], ""
    b[to] = (promo.upper() if p.isupper() else promo) if promo else p
    b[fr] = ""


def legal(s, seat):
    out, king = [], "K" if seat == 0 else "k"
    for m in pseudo(s, seat):
        b = s["b"][:]
        do(b, m[0], m[1], m[2], s["ep"])
        if not attacked(b, b.index(king), 1 - seat):
            out.append(m)
    return out


def advance(s, m):
    """Yangi holat (navbat almashadi). Natija va takrorlanish judge() da hisoblanadi."""
    fr, to, pr = m
    b = s["b"][:]
    p = b[fr]
    cap = bool(b[to]) or (p.lower() == "p" and to == s["ep"] and fr % 8 != to % 8)
    do(b, fr, to, pr, s["ep"])
    cs = s["castle"]
    if p == "K":
        cs = cs.replace("K", "").replace("Q", "")
    elif p == "k":
        cs = cs.replace("k", "").replace("q", "")
    for q in (fr, to):
        if q in CORNER:
            cs = cs.replace(CORNER[q], "")
    pawn = p.lower() == "p"
    return {"b": b, "turn": 1 - s["turn"], "castle": cs, "ep": (fr + to) // 2 if pawn and abs(to - fr) == 16 else -1,
            "half": 0 if cap or pawn else s["half"] + 1, "full": s["full"] + (s["turn"] == 1),
            "last": [fr, to], "res": None, "rep": s["rep"]}


def insufficient(b):
    ps = [(i, p.lower()) for i, p in enumerate(b) if p and p.lower() != "k"]
    if not ps:
        return True
    if len(ps) == 1 and ps[0][1] in "nb":
        return True
    return all(k == "b" for _, k in ps) and len({(i // 8 + i % 8) % 2 for i, _ in ps}) == 1


def judge(s):
    """Yangi holatda natijani (mat, pat, durang) aniqlaydi va takrorlanishni sanaydi."""
    seat = s["turn"]
    lg = legal(s, seat)
    chk = attacked(s["b"], s["b"].index("K" if seat == 0 else "k"), 1 - seat)
    if not lg:
        s["res"] = {"winner": 1 - seat, "reason": "mate"} if chk else {"winner": None, "reason": "stalemate"}
    elif insufficient(s["b"]):
        s["res"] = {"winner": None, "reason": "material"}
    elif s["half"] >= 100:
        s["res"] = {"winner": None, "reason": "fifty"}
    else:
        ep_ok = s["ep"] >= 0 and any(m[1] == s["ep"] and s["b"][m[0]].lower() == "p" and m[0] % 8 != m[1] % 8 for m in lg)
        key = "".join(x or "." for x in s["b"]) + f"{seat}{s['castle']}{s['ep'] if ep_ok else -1}"
        s["rep"] = dict(s["rep"])
        s["rep"][key] = s["rep"].get(key, 0) + 1
        if s["rep"][key] >= 3:
            s["res"] = {"winner": None, "reason": "repetition"}
    return s


def evaluate(b, seat):
    sc = 0
    for sq, p in enumerate(b):
        if not p:
            continue
        k = p.lower()
        r, c = divmod(sq, 8)
        v = VAL[k]
        cen = 3 - max(abs(r - 3.5), abs(c - 3.5))
        if k in "nb":
            v += cen * 6
        elif k == "p":
            v += ((6 - r) if p.isupper() else (r - 1)) * 6 + cen * 2
        sc += v if p.isupper() else -v
    return sc if seat == 0 else -sc


def order(b, lg):
    return sorted(lg, key=lambda m: -VAL[b[m[1]].lower()] if b[m[1]] else 0)


def negamax(s, depth, alpha, beta, ply):
    seat = s["turn"]
    if depth == 0:
        return evaluate(s["b"], seat)
    lg = legal(s, seat)
    if not lg:
        return -99000 + ply if attacked(s["b"], s["b"].index("K" if seat == 0 else "k"), 1 - seat) else 0
    for m in order(s["b"], lg):
        v = -negamax(advance(s, m), depth - 1, -beta, -alpha, ply + 1)
        if v >= beta:
            return v
        alpha = max(alpha, v)
    return alpha


class Chess(Game):
    min_players = max_players = 2

    def new(self, n, options=None):
        s = {"b": START[:], "turn": 0, "castle": "KQkq", "ep": -1, "half": 0, "full": 1, "last": None, "res": None, "rep": {}}
        return judge(s)

    def turn(self, s):
        return None if s["res"] else s["turn"]

    def result(self, s):
        return s["res"]

    def apply(self, s, seat, m):
        if s["res"]:
            raise ValueError("O'yin tugagan")
        if m.get("resign"):
            s["res"] = {"winner": 1 - seat, "reason": "resign"}
            return
        if seat != s["turn"]:
            raise ValueError("Sizning yurishingiz emas")
        fr, to = m.get("from"), m.get("to")
        if type(fr) is not int or type(to) is not int or not (0 <= fr < 64 and 0 <= to < 64):
            raise ValueError("Noto'g'ri katak")
        cand = [x for x in legal(s, seat) if x[0] == fr and x[1] == to]
        if not cand:
            raise ValueError("Noqonuniy yurish")
        pr = str(m.get("promo") or "").lower()
        want = (pr if pr and pr in "qrbn" else "q") if len(cand) > 1 else ""
        n = judge(advance(s, (fr, to, want)))
        s.clear()
        s.update(n)

    def view(self, s, seat):
        v = {k: s[k] for k in ("b", "turn", "last", "res")}
        ks = s["b"].index("K" if s["turn"] == 0 else "k")
        v["check"] = ks if not s["res"] and attacked(s["b"], ks, 1 - s["turn"]) else -1
        if not s["res"] and seat == s["turn"]:
            mv = {}
            for fr, to, _ in legal(s, seat):
                mv.setdefault(str(fr), set()).add(to)
            v["moves"] = {k: sorted(x) for k, x in mv.items()}
        return v

    def bot_move(self, s, seat):
        lg = legal(s, seat)
        random.shuffle(lg)
        best, alpha = None, -10 ** 9
        for m in order(s["b"], lg):
            v = -negamax(advance(s, m), DEPTH - 1, -10 ** 9, -alpha, 1)
            if best is None or v > alpha:
                best, alpha = m, max(alpha, v)
        return {"from": best[0], "to": best[1], "promo": best[2]}


GAME = Chess()
