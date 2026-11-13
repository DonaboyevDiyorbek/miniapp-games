"""Brauzer testi (smoke_client.js) uchun namunaviy holatlarni yaratadi: python tests/make_fixtures.py"""
import json
from pathlib import Path

from server.games.durak.game import GAME as DURAK
from server.games.shaxmat.game import GAME as CHESS
from tests.test_chess import from_fen
from tests.test_durak import mk


def build():
    s = CHESS.new(2)
    att = mk([[[1, 7], [2, 9], [3, 12]], [[1, 8], [0, 9]]], att=0)
    dfn = mk([[[3, 7], [2, 11]], [[1, 8], [0, 9], [3, 6]]], att=0, t=[[[1, 7], None], [[2, 7], None]], phase="defend")
    pas = mk([[[2, 7], [3, 12]], [[1, 9], [0, 9]]], att=0, t=[[[1, 7], [1, 8]]], phase="attack")
    return {
        "start0": CHESS.view(s, 0), "start1": CHESS.view(s, 1),
        "promo": CHESS.view(from_fen("8/P6k/8/8/8/8/8/K7 w - -"), 0),
        "dk_att": DURAK.view(att, 0), "dk_def": DURAK.view(dfn, 1), "dk_pass": DURAK.view(pas, 0),
    }


if __name__ == "__main__":
    (Path(__file__).parent / "fixtures.json").write_text(json.dumps(build()))
