#!/usr/bin/env bash
# Serverni (Ubuntu) bir martada sozlaydi: Python, xizmatlar, HTTPS (Caddy), xavfsizlik devori, kunlik zaxira.
# Ishlatish:  cd /opt/miniapp-games && sudo bash deploy/setup.sh oyinlar.duckdns.org
# Xato bo'lsa tuzatib, qayta ishga tushiravering: skript takroriy ishga tushirishga mos.
set -euo pipefail

DOMAIN="${1:?Domen kerak. Masalan: sudo bash deploy/setup.sh oyinlar.duckdns.org}"
APP=/opt/miniapp-games
OWNER="${SUDO_USER:-root}"

[ "$(id -u)" = 0 ] || { echo "sudo bilan ishga tushiring"; exit 1; }
[ -f "$APP/server/main.py" ] || { echo "Loyiha $APP papkasida bo'lishi kerak (git clone ... $APP)"; exit 1; }
cd "$APP"

echo "==> Paketlar o'rnatilmoqda"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git curl gpg iptables-persistent \
  debian-keyring debian-archive-keyring apt-transport-https

echo "==> Foydalanuvchi va papkalar"
id miniapp >/dev/null 2>&1 || useradd --system --home "$APP" --shell /usr/sbin/nologin miniapp
mkdir -p "$APP/data/backup"
chown -R miniapp:miniapp "$APP/data"

echo "==> Python muhiti"
sudo -u "$OWNER" python3 -m venv "$APP/.venv"
sudo -u "$OWNER" "$APP/.venv/bin/pip" install -q --upgrade pip
sudo -u "$OWNER" "$APP/.venv/bin/pip" install -q -r "$APP/requirements.txt"

echo "==> .env sozlanmoqda"
[ -f "$APP/.env" ] || cp "$APP/.env.example" "$APP/.env"
set_env() {  # set_env KALIT QIYMAT: bor bo'lsa almashtiradi, yo'q bo'lsa qo'shadi
  if grep -q "^$1=" "$APP/.env"; then sed -i "s|^$1=.*|$1=$2|" "$APP/.env"; else echo "$1=$2" >> "$APP/.env"; fi
}
set_env WEBAPP_URL "https://$DOMAIN"
set_env DB_PATH "$APP/data/games.db"
set_env DEV 0
chgrp miniapp "$APP/.env"
chmod 640 "$APP/.env"
if ! grep -Eq '^BOT_TOKEN=[0-9]+:[A-Za-z0-9_-]{30,}$' "$APP/.env"; then
  echo "XATO: $APP/.env ichida BOT_TOKEN to'g'ri yozilmagan (BotFather bergan token kerak)."
  echo "      nano $APP/.env  bilan to'ldiring va bu skriptni qayta ishga tushiring."
  exit 1
fi
grep -Eq '^ADMIN_IDS=[0-9]+' "$APP/.env" || echo "ESLATMA: ADMIN_IDS to'ldirilmagan, admin panel ochilmaydi."

echo "==> Devor (80 va 443 portlar)"
for p in 80 443; do
  iptables -C INPUT -p tcp --dport "$p" -j ACCEPT 2>/dev/null || iptables -I INPUT -p tcp --dport "$p" -j ACCEPT
done
netfilter-persistent save >/dev/null

echo "==> Caddy (avtomatik HTTPS)"
if ! command -v caddy >/dev/null 2>&1; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi
cat > /etc/caddy/Caddyfile <<CADDY
$DOMAIN {
    encode gzip
    reverse_proxy 127.0.0.1:8000
}
CADDY
systemctl enable caddy >/dev/null 2>&1
systemctl restart caddy

echo "==> Xizmatlar"
cp deploy/miniapp-api.service deploy/miniapp-bot.service /etc/systemd/system/
chmod +x deploy/backup.sh deploy/update.sh
echo "0 4 * * * miniapp $APP/deploy/backup.sh >> $APP/data/backup/backup.log 2>&1" > /etc/cron.d/miniapp-backup
systemctl daemon-reload
systemctl enable miniapp-api miniapp-bot >/dev/null 2>&1
systemctl restart miniapp-api miniapp-bot

sleep 3
echo "==> Tekshiruv"
if curl -fsS http://127.0.0.1:8000/api/games; then
  echo; echo "OK: server ishlayapti. Endi brauzerda https://$DOMAIN ni oching (HTTPS sertifikat 1-2 daqiqada tayyor bo'ladi)"
  echo "    va Telegramda botingizga /start yozing."
else
  echo "XATO: server javob bermadi. Qarang: journalctl -u miniapp-api -n 50 --no-pager"; exit 1
fi
