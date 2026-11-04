# ⚠️ HAFTALIK AGENT UCHUN MUHIM (2026-11-04 dan)

**Metricool ishlatilmaydi** — unda Instagram ulanmagan (getBrandSettings "no social network connected" qaytaradi).
Postlar o'zimizning bepul rejalashtirgich orqali chiqadi:

- Reja: `reja/posts.json` — ro'yxat. Element:
  `{"id": "unikal-id", "at": "2026-11-06T10:00", "type": "REEL"|"STORY"|"POST", "media": ["repo:reels/<nom>-ovoz.mp4"], "caption": "..."}`
  (vaqt Asia/Samarkand; STORY uchun caption bo'sh; media `repo:stories/<nom>.jpg` ham bo'ladi).
- Chiqaruvchi: `.github/workflows/ig-post.yml` + `tools/ig_publish.py` (har 15 daqiqada, holat `reja/holat.json`).
- Mavjud elementlarni o'chirma/o'zgartirma, vaqtlar ustma-ust tushmasin. Tekshiruv: `python3 tools/ig_publish.py --dry`.
- Yo'riqnomadagi Metricool qadamlari (getBrandSettings, getScheduledPosts, createScheduledPost, audioId) o'rniga shu fayl ishlatiladi.
  Fon musiqasi Instagram audioId bilan emas — kerak bo'lsa videoga o'zing past qilib qo'sh.
- Hisobot uchun: `reja/ig-stat.json`, `reja/tahlil.json`, `reja/holat.json`.

# Metartshop Reels avtomatika
- `python3 tools/reels_gen.py specs.json` -> out/*.mp4 (1080x1920, ovozsiz; musiqa Metricool orqali Instagram kutubxonasidan qo'shiladi)
- Rasm yo'llari repo ildiziga nisbatan: `img/...` (sayt mahsulotlari), `ig/src/<id>.jpg` (ustaxona suratlari, ro'yxat ig/src/README.json), `yangi/...` (egasi qo'shgan yangi suratlar).
- `@` prefiksi rasmni 90° buradi; `"white":true` oq fonli chizmalar uchun.
- Namuna: tools/specs-hafta1.json
- Videolar `reels/` ga yuklanadi, URL: https://oybekkjon1994-coder.github.io/metartshop/reels/<nom>.mp4
