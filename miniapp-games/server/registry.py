"""O'yin plaginlarini topish va yuklash: server/games/<id>/{manifest.json, game.py, client.js}"""
import importlib.util, io, json, re, shutil, zipfile
from pathlib import Path, PurePosixPath

from server.games.base import Game

GAMES_DIR = Path(__file__).parent / "games"
ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,30}$")
MAX_UNZIPPED = 1_000_000


class Registry:
    def __init__(self, games_dir=GAMES_DIR):
        self.dir = Path(games_dir)
        self.games, self.meta = {}, {}

    def load(self):
        for d in sorted(self.dir.iterdir()):
            if d.is_dir() and (d / "manifest.json").exists():
                try:
                    self._load(d)
                except Exception as e:  # bitta buzuq plagin serverni yiqitmasin
                    print(f"[registry] {d.name} o'tkazib yuborildi: {e}")

    def _load(self, d: Path):
        m = json.loads((d / "manifest.json").read_text("utf-8"))
        gid = m.get("id")
        if not isinstance(gid, str) or not ID_RE.match(gid) or gid != d.name:
            raise ValueError("manifest id papka nomiga teng va [a-z0-9_] bo'lishi kerak")
        for f in ("game.py", "client.js"):
            if not (d / f).exists():
                raise ValueError(f"{f} topilmadi")
        spec = importlib.util.spec_from_file_location(f"plugin_{gid}", d / "game.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        g = mod.GAME
        if not isinstance(g, Game):
            raise ValueError("GAME o'zgaruvchisi Game'dan meros olishi kerak")
        g.id, g.name = gid, m.get("name", gid)
        self.games[gid], self.meta[gid] = g, m

    def install_zip(self, data: bytes) -> str:
        """Admin yuklagan ZIP ni o'rnatadi. DIQQAT: game.py serverda ishga tushadi (faqat ishonchli adminlar!)."""
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile:
            raise ValueError("ZIP fayl emas")
        infos = [i for i in z.infolist() if not i.is_dir() and not i.filename.startswith("__MACOSX/")]
        if not infos or len(infos) > 50 or sum(i.file_size for i in infos) > MAX_UNZIPPED:
            raise ValueError("Arxiv hajmi yoki tarkibi noto'g'ri")
        names = [i.filename for i in infos]
        top = names[0].split("/")[0] + "/"
        strip = "manifest.json" not in names and all(n.startswith(top) for n in names)
        files = {}
        for i in infos:
            n = i.filename[len(top):] if strip else i.filename
            p = PurePosixPath(n)
            if p.is_absolute() or ".." in p.parts or "\\" in n:
                raise ValueError("Xavfli fayl yo'li")
            files[str(p)] = i
        if "manifest.json" not in files:
            raise ValueError("manifest.json yo'q")
        try:
            gid = json.loads(z.read(files["manifest.json"]))["id"]
        except Exception:
            raise ValueError("manifest.json noto'g'ri")
        if not isinstance(gid, str) or not ID_RE.match(gid):
            raise ValueError("O'yin id noto'g'ri")
        dest, tmp = self.dir / gid, self.dir / f".tmp_{gid}"
        if dest.exists():
            raise ValueError("Bunday o'yin allaqachon bor")
        shutil.rmtree(tmp, ignore_errors=True)
        try:
            for n, i in files.items():
                t = tmp / n
                t.parent.mkdir(parents=True, exist_ok=True)
                t.write_bytes(z.read(i))
            tmp.rename(dest)
            self._load(dest)
        except Exception as e:
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(dest, ignore_errors=True)
            self.games.pop(gid, None)
            self.meta.pop(gid, None)
            raise ValueError(f"Plagin yuklanmadi: {e}") from e
        return gid
