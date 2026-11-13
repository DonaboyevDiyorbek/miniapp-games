"""O'yin plagini interfeysi. O'yin = sof Python qoidalar mexanizmi; state JSON bo'lishi shart."""


class Game:
    id = ""            # manifest.json dagi id bilan to'ldiriladi
    name = ""
    min_players = 2
    max_players = 2

    def new(self, n: int, options: dict | None = None) -> dict:
        """n ta o'yinchi uchun boshlang'ich holat."""
        raise NotImplementedError

    def view(self, state: dict, seat: int) -> dict:
        """seat o'yinchiga ko'rsatiladigan holat (yashirin ma'lumotni olib tashlang)."""
        return state

    def turn(self, state: dict):
        """Kimning yurishi (seat raqami) yoki o'yin tugagan bo'lsa None."""
        raise NotImplementedError

    def apply(self, state: dict, seat: int, move: dict) -> None:
        """Yurishni qo'llash. Noqonuniy bo'lsa ValueError('sabab')."""
        raise NotImplementedError

    def result(self, state: dict):
        """Tugamagan bo'lsa None, aks holda {"winner": seat|None, "reason": str}."""
        return None

    def bot_move(self, state: dict, seat: int):
        """Ixtiyoriy: robot yurishi. Qo'llab-quvvatlamasangiz o'zgartirmang."""
        return None
