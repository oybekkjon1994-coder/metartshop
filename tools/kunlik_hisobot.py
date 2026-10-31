"""Kunlik hisobot — dollar, ob-havo, Instagram, bugungi postlar.
GitHub Actions'da ishlaydi (bepul). Natijani Telegram'ga yuboradi (TG_TOKEN + TG_CHAT).
Claude kerak emas — hammasi ochiq, bepul manbalardan."""
import os, json, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=5))  # Asia/Samarkand
BUGUN = datetime.now(TZ)
API = "https://graph.facebook.com/v21.0"


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "metartshop-bot"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def dollar():
    try:
        d = get("https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/")
        u = d[0]
        rate = float(u["Rate"])
        diff = float(u.get("Diff") or 0)
        ok = f"{rate:,.0f} so'm".replace(",", " ")
        if diff:
            yon = "▲" if diff > 0 else "▼"
            ok += f" ({yon} {abs(diff):,.0f})".replace(",", " ")
        return ok
    except Exception as e:
        return f"(olinmadi: {e})"


WCODE = {0: "ochiq", 1: "asosan ochiq", 2: "bulutli", 3: "to'liq bulutli",
         45: "tuman", 48: "tuman", 51: "mayda yomg'ir", 53: "yomg'ir", 55: "yomg'ir",
         61: "yomg'ir", 63: "yomg'ir", 65: "kuchli yomg'ir", 71: "qor", 73: "qor",
         75: "kuchli qor", 80: "jala", 81: "jala", 82: "kuchli jala",
         95: "momaqaldiroq", 96: "momaqaldiroq"}


def obhavo():
    try:
        d = get("https://api.open-meteo.com/v1/forecast?latitude=41.31&longitude=69.24"
                "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min"
                "&timezone=Asia/Tashkent")
        c = d["current"]
        t = round(c["temperature_2m"])
        desc = WCODE.get(c.get("weather_code"), "")
        hi = round(d["daily"]["temperature_2m_max"][0])
        lo = round(d["daily"]["temperature_2m_min"][0])
        return f"{t}°C, {desc} (bugun {lo}…{hi}°C)"
    except Exception as e:
        return f"(olinmadi: {e})"


def instagram():
    tok = os.environ.get("IG_TOKEN")
    ig = os.environ.get("IG_USER_ID") or os.environ.get("IG_DEFAULT_ID", "17841470082191241")
    foll = "?"
    try:
        if tok:
            a = get(f"{API}/{ig}?fields=followers_count&access_token={urllib.parse.quote(tok)}")
            foll = f"{a.get('followers_count','?'):,}".replace(",", " ")
    except Exception:
        pass
    # kecha chiqqan postlar — holat.json
    kecha = (BUGUN - timedelta(days=1)).strftime("%Y-%m-%d")
    n = 0
    try:
        holat = json.load(open("reja/holat.json", encoding="utf-8"))
        for k, v in holat.items():
            if k.startswith("_") or not isinstance(v, dict):
                continue
            if v.get("status") == "chiqdi" and str(v.get("vaqt", "")).startswith(kecha):
                n += 1
    except Exception:
        pass
    return foll, n


def bugungi_postlar():
    sana = BUGUN.strftime("%Y-%m-%d")
    try:
        d = json.load(open("reja/posts.json", encoding="utf-8"))
        posts = d if isinstance(d, list) else d.get("posts", [])
        bugun = [p for p in posts if str(p.get("at", "")).startswith(sana)]
        bugun.sort(key=lambda p: p.get("at", ""))
        return bugun
    except Exception:
        return []


def yubor(text):
    tok, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not (tok and chat):
        print("TG_TOKEN/TG_CHAT yo'q — faqat chop etaman:\n", text)
        return
    data = urllib.parse.urlencode({"chat_id": chat, "text": text,
                                   "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20)
    print("Yuborildi.")


def main():
    foll, kecha_n = instagram()
    posts = bugungi_postlar()
    hafta = ["Dush", "Sesh", "Chor", "Pay", "Jum", "Shan", "Yak"][BUGUN.weekday()]

    L = [f"📅 Kunlik hisobot — {BUGUN.strftime('%d.%m.%Y')} ({hafta})", ""]
    L += [f"💵 Dollar: {dollar()}", f"🌤 Toshkent: {obhavo()}", ""]
    L += ["📸 Instagram (@metart_shop)",
          f"   • Obunachi: {foll}",
          f"   • Kecha chiqdi: {kecha_n} ta post", ""]
    if posts:
        L.append(f"📋 Bugun rejada: {len(posts)} ta")
        for p in posts[:10]:
            vaqt = p.get("at", "")[11:16]
            typ = "🎬" if "REEL" in p.get("type", "").upper() else ("📖" if "STOR" in p.get("type", "").upper() else "🖼")
            L.append(f"   {vaqt} {typ} {p.get('id')}")
    else:
        L.append("📋 Bugun rejada post yo'q")
    L += ["", "— Metartshop avto-hisobot"]
    yubor("\n".join(L))


if __name__ == "__main__":
    main()
