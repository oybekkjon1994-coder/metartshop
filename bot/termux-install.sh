#!/data/data/com.termux/files/usr/bin/bash
# METARTSHOP bot — eski Android telefonda 24/7 ishlatish (Termux). Bepul, karta kerak emas.
# Termux'da bitta buyruq:
#   curl -fsSL https://raw.githubusercontent.com/oybekkjon1994-coder/metartshop/main/bot/termux-install.sh | bash
set -e
DIR="$HOME/metartshop"
echo "== 1/4 Paketlar o'rnatilmoqda (bir necha daqiqa) =="
yes | pkg update -y >/dev/null 2>&1 || true
pkg install -y nodejs-lts git termux-api >/dev/null 2>&1 || pkg install -y nodejs-lts git

echo "== 2/4 Bot yuklab olinmoqda =="
if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q --depth 1 https://github.com/oybekkjon1994-coder/metartshop.git "$DIR"; fi
cd "$DIR/bot"
# Android uchun rasm kutubxonasining WebAssembly versiyasi (hamma telefonda ishlaydi)
npm install --omit=dev --no-audit --no-fund --cpu=wasm32 --os=linux sharp@0.35.4 >/dev/null
node -e "require('sharp')" && echo "   rasm kutubxonasi: OK"

echo "== 3/4 Sozlash =="
if [ ! -f .env ]; then
  printf "BotFather bergan TOKENni kiriting: "; read -r TOKEN </dev/tty
  printf "Admin kodi (kamida 8 belgi, bo'sh qoldirsangiz o'zim yarataman): "; read -r CODE </dev/tty
  [ ${#CODE} -ge 8 ] || CODE=$(od -An -N8 -tx1 /dev/urandom | tr -d ' \n')
  printf "BOT_TOKEN=%s\nADMIN_CODE=%s\n" "$TOKEN" "$CODE" > .env
  echo "   Admin kodingiz: $CODE  (botga /admin $CODE deb yozing)"
fi

# Ishga tushirish skripti: xato bo'lsa qayta yoqiladi
cat > "$HOME/bot.sh" <<'EOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock 2>/dev/null
cd "$HOME/metartshop/bot"
set -a; . ./.env; set +a
while true; do
  node src/bot.js; code=$?
  [ $code -eq 2 ] && { echo "TOKEN noto'g'ri — ~/metartshop/bot/.env ni tuzating"; exit 2; }
  echo "Bot to'xtadi ($code), 5 soniyadan keyin qayta yoqiladi..."; sleep 5
done
EOF
chmod +x "$HOME/bot.sh"
# Telefon qayta yonganda avtomatik (Termux:Boot ilovasi o'rnatilgan bo'lsa)
mkdir -p "$HOME/.termux/boot" && cp "$HOME/bot.sh" "$HOME/.termux/boot/metartshop-bot"
# Termux ochilganda bot o'chiq bo'lsa yoqiladi
grep -q metartshop-auto "$HOME/.bashrc" 2>/dev/null || echo 'pgrep -f "src/bot.js" >/dev/null || { echo "Bot yoqilmoqda..."; nohup ~/bot.sh >~/bot.log 2>&1 & } # metartshop-auto' >> "$HOME/.bashrc"

echo "== 4/4 Bot yoqilmoqda =="
pgrep -f "src/bot.js" >/dev/null || nohup "$HOME/bot.sh" > "$HOME/bot.log" 2>&1 &
sleep 8; tail -5 "$HOME/bot.log"
echo
echo "TAYYOR. Kompyuterdagi bot oynasini YOPING (ikkalasi birga ishlamaydi)."
echo "Jurnal: tail -f ~/bot.log    Yangilash: shu buyruqni qayta ishga tushiring."
