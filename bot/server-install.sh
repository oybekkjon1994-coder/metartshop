#!/usr/bin/env bash
# METARTSHOP botini Linux serverga (Oracle Cloud, VPS) o'rnatish.
# Ishlatish:  curl -fsSL https://raw.githubusercontent.com/oybekkjon1994-coder/metartshop/main/bot/server-install.sh | sudo bash
set -euo pipefail
DIR=/opt/metartshop-bot
echo "== Node.js o'rnatilmoqda =="
if ! command -v node >/dev/null || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]; then
  apt-get update -y && apt-get install -y curl ca-certificates git
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi
echo "== Bot fayllari yuklanmoqda =="
TMP=$(mktemp -d)
git clone --depth 1 https://github.com/oybekkjon1994-coder/metartshop "$TMP/repo"
mkdir -p "$DIR"
cp -r "$TMP/repo/bot/src" "$TMP/repo/bot/package.json" "$TMP/repo/bot/config.json" "$DIR/"
rm -rf "$TMP"
cd "$DIR" && npm install --omit=dev --no-audit --no-fund
if [ ! -f "$DIR/.env" ]; then
  read -r -p "BotFather bergan tokenni kiriting: " TOKEN </dev/tty
  CODE=$(( RANDOM * RANDOM % 900000 + 100000 ))
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
Restart=always
RestartSec=5
Environment=NODE_ENV=production
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now metartshop-bot
sleep 3
systemctl --no-pager status metartshop-bot | head -5 || true
echo
echo "✅ Bot serverda ishga tushdi va server qayta yoqilsa ham o'zi ishlaydi."
echo "   Admin bo'lish uchun botga yozing:  /admin $(grep ADMIN_CODE $DIR/.env | cut -d= -f2)"
echo "   Yangilash uchun shu buyruqni qayta ishga tushiring (buyurtmalar saqlanib qoladi)."
echo "   Jurnal: journalctl -u metartshop-bot -f"
