@echo off
chcp 65001 >nul
title METARTSHOP bot
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js topilmadi. https://nodejs.org saytidan LTS versiyasini o'rnating. & pause & exit /b)
if not exist ".env" (
  echo BOT_TOKEN=SHU_YERGA_TOKENNI_YOZING> .env
  echo ADMIN_CODE=%RANDOM%%RANDOM%%RANDOM%%RANDOM%%RANDOM%>> .env
  echo.
  echo .env fayli yaratildi. Bloknot ochiladi: BOT_TOKEN qatoriga BotFather bergan tokenni yozing, saqlang va yoping.
  notepad .env
)
if not exist "node_modules\sharp" (
  echo Kutubxonalar o'rnatilmoqda, 1-2 daqiqa kuting...
  call npm install --omit=dev
  if not exist "node_modules\sharp" (echo Kutubxonalar o'rnatilmadi. Internetni tekshirib, start.bat ni qayta oching. & pause & exit /b)
)
echo.
echo Admin kodi:
findstr ADMIN_CODE .env
echo Botga "/admin KOD" deb yozsangiz, buyurtmalar sizga keladi.
echo.
:loop
node src\bot.js
if %errorlevel%==2 (echo Tokenni .env faylida to'g'rilang va start.bat ni qayta oching. & notepad .env & pause & exit /b)
echo Bot to'xtadi. 5 soniyadan keyin qayta ishga tushadi (butunlay yopish uchun oynani yoping)...
timeout /t 5 >nul
goto loop
