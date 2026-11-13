#!/usr/bin/env bash
# Yangi kodni GitHub'dan olib, xizmatlarni qayta ishga tushiradi.
# DIQQAT: davom etayotgan o'yinlar uziladi (xonalar xotirada). Odamlar kam vaqtda ishga tushiring.
# Ishlatish (oddiy foydalanuvchi sifatida, sudo'siz):  bash /opt/miniapp-games/deploy/update.sh
set -euo pipefail
cd /opt/miniapp-games
git pull --ff-only
.venv/bin/pip install -q -r requirements.txt
sudo systemctl restart miniapp-api miniapp-bot
sleep 2
curl -fsS http://127.0.0.1:8000/api/games >/dev/null && echo "Yangilandi, server ishlayapti."
