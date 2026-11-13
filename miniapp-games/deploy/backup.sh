#!/usr/bin/env bash
# Bazaning kunlik zaxirasi (reyting!). setup.sh uni har kuni 04:00 da ishga tushiradi. 14 kundan eskisi o'chadi.
set -euo pipefail
D=/opt/miniapp-games/data
[ -f "$D/games.db" ] || exit 0
mkdir -p "$D/backup"
python3 - "$D" <<'PY'
import sqlite3, sys, time
d = sys.argv[1]
src = sqlite3.connect(f"{d}/games.db")
dst = sqlite3.connect(f"{d}/backup/games-{time.strftime('%Y%m%d')}.db")
src.backup(dst)
dst.close(); src.close()
PY
find "$D/backup" -name 'games-*.db' -mtime +14 -delete
