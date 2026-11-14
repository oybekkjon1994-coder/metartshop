# METARTSHOP Telegram bot

Mijozlar uchun bot:
- **🛍 Katalog**: saytdagi mahsulotlar (`data.json`) avtomatik chiqadi, narx va rasmlari bilan. Saytga mahsulot qo'shsangiz, botda ham paydo bo'ladi.
- **⚽ Klub soatlari**: futbol klublari soatlari ro'yxati.
- **🎨 O'z dizaynim**: mijoz logotip yoki rasm yuboradi, bot darhol soatning taxminiy ko'rinishini chiqaradi. Mijoz o'lcham va rang tanlaydi. Buyurtma kelganda sizga **lazer uchun DXF** keladi: bir butun detal, bo'laklar ko'prik bilan ulangan, markazda soat mexanizmi uchun 8 mm teshik.
- **Buyurtma**: rang → soni → ism → telefon → yetkazish (Toshkent Yandex / viloyat BTS / o'zi olib ketadi) → manzil → tasdiqlash.
- **📦 Buyurtmalarim**: mijoz o'z buyurtmasining holatini ko'radi.
- O'zbek va rus tillarida ishlaydi.

## Ishga tushirish (Windows)
1. Kompyuterda **Node.js** (20 yoki undan yangi) bo'lishi kerak.
2. `start.bat` ni ikki marta bosing.
3. Birinchi ishga tushishda Bloknot ochiladi: `BOT_TOKEN=` qatoriga @BotFather bergan tokenni yozing, saqlang va yoping.
4. Oynada **Admin kodi** chiqadi. Telegram'da botga `/admin KOD` deb yozing. Shundan keyin yangi buyurtmalar sizga keladi.

Bot kompyuter yoqiq va `start.bat` oynasi ochiq turgan paytda ishlaydi.

## Admin buyruqlari
- `/buyurtmalar`: oxirgi buyurtmalar. Holatini tugma bilan o'zgartirasiz: ✅ Qabul / 🔧 Tayyorlanmoqda / 🚚 Jo'natildi / 🎉 Topshirildi / ❌ Bekor. Mijozga holat haqida avtomatik xabar boradi.
- `/statistika`: foydalanuvchilar, buyurtmalar, summa.
- `/referal`: do'st taklifi hisoboti — havola orqali kelganlar, ulardan buyurtmalar, top-10 taklifchilar va sovg'a berilishi kerak bo'lganlar.
- `/xabar MATN`: botdan foydalangan barcha mijozlarga xabar yuboradi (aksiya va yangiliklar uchun). Rasm bilan yuborish uchun rasmni jo'natib, izohiga `/xabar ...` deb yozing.
- `/ilova`: «Lazer ustaxona» ilovasining eng yangi APK sini (GitHub Releases, `lazer-app` → `lazer.apk`) ilovani botdan so'ragan mijozlarga yuboradi. `/ilova hammaga` — botdan foydalangan barchaga. Ilovadagi «O'rnatish» tugmasi (`?start=ilova_yangilash`) bosilganda ham bot APK ni o'zi yuboradi.

## Sozlamalar (`config.json`)
- `referral`: do'st taklifi. `percent` — do'st va taklif qiluvchiga chegirma (%). `levels` — darajalar: `at` ta do'sti buyurtma olgach `percent` (chegirma kuponi, avtomatik) yoki `gift` (sovg'a, adminga xabar keladi va qo'lda berasiz). Mijoz «🎁 Chegirma olish» da progress, darajalar va «🏆 Reyting» ni ko'radi.
- `custom_sizes`: "O'z dizaynim" uchun o'lcham (sm) va narxlar.
- `custom_colors`: tanlanadigan ranglar.

## Instagram uchun havolalar
- `https://t.me/BOT_NOMI?start=dizayn`: to'g'ridan-to'g'ri "O'z dizaynim" ochiladi.
- `https://t.me/BOT_NOMI?start=klub`: klub soatlari ro'yxati.
- `https://t.me/BOT_NOMI?start=p_barselona-soat`: bitta mahsulot (`p_` + saytdagi mahsulot id).

Buyurtmalar, mijozlar va DXF fayllar `data/` papkasida saqlanadi.
