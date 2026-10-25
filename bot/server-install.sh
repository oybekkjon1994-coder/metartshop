#!/usr/bin/env bash
# METARTSHOP botini Linux serverga (Oracle Cloud, VPS) o'rnatish.
# Ishlatish:  curl -fsSL https://raw.githubusercontent.com/oybekkjon1994-coder/metartshop/main/bot/server-install.sh | sudo bash
set -euo pipefail
DIR=/opt/metartshop-bot
if ! command -v apt-get >/dev/null; then echo "Bu skript faqat Ubuntu/Debian uchun. Serverda Ubuntu tanlang."; exit 1; fi
echo "== Kerakli dasturlar o'rnatilmoqda =="
apt-get update -y && apt-get install -y curl ca-certificates git openssl
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
id metartbot >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin metartbot
echo "== Bot fayllari yuklanmoqda =="
TMP=$(mktemp -d)
git clone --depth 1 https://github.com/oybekkjon1994-coder/metartshop "$TMP/repo"
mkdir -p "$DIR"
cp -r "$TMP/repo/bot/src" "$TMP/repo/bot/package.json" "$DIR/"
[ -f "$DIR/config.json" ] || cp "$TMP/repo/bot/config.json" "$DIR/"   # narxlaringiz yangilanishda saqlanib qoladi
rm -rf "$TMP"
cd "$DIR" && npm install --omit=dev --no-audit --no-fund
if [ ! -f "$DIR/.env" ]; then
  TOKEN=""
  while ! [[ "$TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{30,}$ ]]; do read -r -p "BotFather bergan tokenni kiriting: " TOKEN </dev/tty; done
  CODE=$(openssl rand -hex 8)
  printf 'BOT_TOKEN=%s\nADMIN_CODE=%s\n' "$TOKEN" "$CODE" > "$DIR/.env"
  chmod 600 "$DIR/.env"
fi
cat > /etc/systemd/system/metartshop-bot.service <<UNIT
[Unit]
Description=METARTSHOP Telegram bot
After=network-online.target
Wants=network-online.target
[Service]
WorkingDirectory=$DIR
ExecStart=$(command -v node) src/bot.js
User=metartbot
Restart=always
RestartSec=5
Environment=NODE_ENV=production
[Install]
WantedBy=multi-user.target
UNIT
mkdir -p "$DIR/data" && chown -R metartbot "$DIR/data" && chown metartbot "$DIR/.env"
systemctl daemon-reload
systemctl enable metartshop-bot && systemctl restart metartshop-bot
sleep 3
systemctl --no-pager status metartshop-bot | head -5 || true
echo
echo "✅ Bot serverda ishga tushdi va server qayta yoqilsa ham o'zi ishlaydi."
echo "   Admin kodi:  sudo grep ADMIN_CODE $DIR/.env   (botga  /admin KOD  deb yozing)"
echo "   Yangilash uchun shu buyruqni qayta ishga tushiring (buyurtmalar saqlanib qoladi)."
echo "   Jurnal: journalctl -u metartshop-bot -f"
