import json, shutil, subprocess, unittest
from pathlib import Path


@unittest.skipUnless(shutil.which("node"), "node o'rnatilmagan")
class ClientSmoke(unittest.TestCase):
    def test_node_smoke(self):
        root = Path(__file__).resolve().parent.parent
        from tests.make_fixtures import build
        (root / "tests" / "fixtures.json").write_text(json.dumps(build()))
        r = subprocess.run(["node", "tests/smoke_client.js"], cwd=root, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
