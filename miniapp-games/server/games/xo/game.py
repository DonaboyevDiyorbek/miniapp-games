import random
from server.games.base import Game

LINES = [(0, 1, 2), (3, 4, 5), (6, 7, 8), (0, 3, 6), (1, 4, 7), (2, 5, 8), (0, 4, 8), (2, 4, 6)]


def winner_line(b):
    for l in LINES:
        if b[l[0]] is not None and b[l[0]] == b[l[1]] == b[l[2]]:
            return l
    return None


class XO(Game):
    min_players = max_players = 2

    def new(self, n, options=None):
        return {"b": [None] * 9, "turn": 0}

    def turn(self, s):
        return None if self.result(s) else s["turn"]

    def apply(self, s, seat, m):
        if self.result(s):
            raise ValueError("O'yin tugagan")
        if seat != s["turn"]:
            raise ValueError("Sizning yurishingiz emas")
        i = m.get("cell")
        if type(i) is not int or not 0 <= i < 9 or s["b"][i] is not None:
            raise ValueError("Noto'g'ri katak")
        s["b"][i] = seat
        s["turn"] = 1 - seat

    def result(self, s):
        l = winner_line(s["b"])
        if l:
            return {"winner": s["b"][l[0]], "reason": "line", "line": list(l)}
        if all(x is not None for x in s["b"]):
            return {"winner": None, "reason": "draw"}
        return None

    def bot_move(self, s, seat):
        b = s["b"]
        free = [i for i in range(9) if b[i] is None]
        for who in (seat, 1 - seat):          # avval yutish, keyin to'sish
            for i in free:
                b[i] = who
                hit = winner_line(b)
                b[i] = None
                if hit:
                    return {"cell": i}
        return {"cell": 4 if 4 in free else random.choice(free)}


GAME = XO()
