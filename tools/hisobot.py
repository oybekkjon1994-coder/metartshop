"""Metartshop agenti: ertalabki hisobot, haftalik tahlil va xatolik signali -> Telegram.

  python tools/hisobot.py morning   # har kuni 08:00 (Toshkent)
  python tools/hisobot.py weekly    # dushanba 09:00
  python tools/hisobot.py alert     # har 30 daqiqada, faqat muammo bo'lsa yozadi
  qo'shimcha: --dry  (Telegram'ga yubormaydi, matnni ekranga chiqaradi)

GitHub Actions'da ishlaydi (bepul). Kerakli secrets: IG_TOKEN, IG_USER_ID, TG_TOKEN, TG_CHAT.
Holat: reja/hisobot-holat.json
"""
import os, sys, json, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=5))  # Asia/Tashkent
API = "https://graph.facebook.com/v21.0"
STATE = "reja/hisobot-holat.json"
DRY = "--dry" in sys.argv


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "metartshop"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def save_state(st):
    if DRY:
        return
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def notify(text):
    print("----- XABAR -----\n" + text + "\n-----------------")
    tok, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if DRY or not tok or not chat:
        if not DRY:
            print("TG_TOKEN/TG_CHAT yo'q - xabar yuborilmadi")
        return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:4000],
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20)
    except Exception as e:
        print("Telegram xato:", e)


def parse_at(s):
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=TZ)


def nf(n):
    return f"{n:,.0f}".replace(",", " ")


# ---------- ma'lumot olish ----------
def usd_rate():
    for url, fn in (("https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/", lambda d: float(d[0]["Rate"])),
                    ("https://open.er-api.com/v6/latest/USD", lambda d: float(d["rates"]["UZS"]))):
        try:
            return fn(get(url, 10)), ("CBU" if "cbu" in url else "bozor")
        except Exception:
            pass
    return None, None


def weather():
    try:
        d = get("https://api.open-meteo.com/v1/forecast?latitude=41.31&longitude=69.24"
                "&current=temperature_2m&daily=temperature_2m_max,temperature_2m_min&timezone=Asia/Tashkent", 10)
        return round(d["current"]["temperature_2m"]), round(d["daily"]["temperature_2m_min"][0]), round(d["daily"]["temperature_2m_max"][0])
    except Exception:
        return None


def ig_account():
    tok = os.environ.get("IG_TOKEN")
    if not tok:
        return None
    q = urllib.parse.urlencode({"access_token": tok})
    uid = os.environ.get("IG_USER_ID", "").strip()
    try:
        if not uid:
            pages = get(f"{API}/me/accounts?fields=instagram_business_account&{q}")["data"]
            uid = next(p["instagram_business_account"]["id"] for p in pages if p.get("instagram_business_account"))
        acc = get(f"{API}/{uid}?fields=followers_count,media_count,username&{q}")
        media = get(f"{API}/{uid}/media?fields=caption,like_count,comments_count,media_type,permalink,timestamp&limit=50&{q}").get("data", [])
        return {"id": uid, "followers": acc.get("followers_count"), "media": media}
    except Exception as e:
        print("Instagram API xato:", str(e)[:200])
        return None


def media_time(m):
    return datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(TZ)


def score(m):
    return (m.get("like_count") or 0) + 3 * (m.get("comments_count") or 0)


def short(s, n=40):
    s = (s or "").replace("\n", " ").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


# ---------- ertalabki hisobot ----------
def morning(st):
    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    yday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    posts = load("reja/posts.json", [])
    holat = load("reja/holat.json", {})
    lines = [f"☀️ Xayrli tong! {now.strftime('%d.%m.%Y')}"]

    rate, src = usd_rate()
    if rate:
        prev = st.get("usd")
        d = f" ({rate - prev:+,.0f})".replace(",", " ") if prev else ""
        lines.append(f"💵 Dollar: {nf(rate)} so'm{d} · {src}")
        st["usd"] = rate
    w = weather()
    if w:
        lines.append(f"🌤 Toshkent: {w[0]}° (bugun {w[1]}…{w[2]}°)")

    ig = ig_account()
    if ig and ig.get("followers") is not None:
        prevf = st.get("followers")
        d = f" ({ig['followers'] - prevf:+d})" if prevf is not None else ""
        lines.append(f"📸 @metart_shop: {nf(ig['followers'])} obunachi{d}")
        st["followers"] = ig["followers"]
        if not DRY:
            h = load("reja/ig-tarix.json", {})
            h[today] = ig["followers"]
            json.dump(dict(sorted(h.items())[-400:]), open("reja/ig-tarix.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        yd = [m for m in ig["media"] if media_time(m).strftime("%Y-%m-%d") == yday]
        if yd:
            best = max(yd, key=score)
            lines.append(f"🎬 Kecha {len(yd)} ta post. Eng yaxshisi: {short(best.get('caption'))} "
                         f"(❤ {best.get('like_count', 0)} 💬 {best.get('comments_count', 0)})")
        else:
            lines.append("🎬 Kecha post chiqmagan")
    else:
        done = sum(1 for k, v in holat.items() if not k.startswith("_") and v.get("status") == "chiqdi"
                   and str(v.get("vaqt", "")).startswith(yday))
        lines.append(f"🎬 Kecha chiqqan postlar: {done}")

    todays = sorted((parse_at(p["at"]), p) for p in posts
                    if not p["id"].startswith("_") and p["at"].startswith(today)
                    and holat.get(p["id"], {}).get("status") not in ("chiqdi", "o'tkazildi"))
    if todays:
        lines.append("🗓 Bugun rejada:")
        for at, p in todays:
            kind = "story" if p.get("type") == "STORY" else "reel" if p.get("type") == "REEL" else "post"
            lines.append(f"  {at.strftime('%H:%M')} · {kind} · {p['id']}")
    else:
        lines.append("🗓 Bugun rejalashtirilgan post yo'q")

    ti = load("reja/token_info.json", {})
    if ti.get("days_left") is not None and ti["days_left"] < 15:
        lines.append(f"🔑 Instagram tokeni {ti['days_left']:.0f} kundan keyin tugaydi - yangilang")
    notify("\n".join(lines))


# ---------- haftalik tahlil ----------
def weekly(st):
    ig = ig_account()
    if not ig:
        notify("📊 Haftalik tahlil: Instagram ma'lumotini olib bo'lmadi (token yoki ulanish xatosi).")
        return
    now = datetime.now(TZ)
    media = ig["media"]
    week = [m for m in media if now - media_time(m) <= timedelta(days=7)]
    lines = ["📊 Haftalik hisobot (@metart_shop)"]
    prevf = st.get("followers_week")
    d = f" ({ig['followers'] - prevf:+d} hafta ichida)" if prevf is not None else ""
    lines.append(f"👥 {nf(ig['followers'])} obunachi{d}")
    st["followers_week"] = ig["followers"]
    if week:
        likes = sum(m.get("like_count") or 0 for m in week)
        comm = sum(m.get("comments_count") or 0 for m in week)
        lines.append(f"🎬 {len(week)} ta post · ❤ {likes} · 💬 {comm}")
        ranked = sorted(week, key=score, reverse=True)
        lines.append("🏆 Eng yaxshi:")
        for m in ranked[:3]:
            lines.append(f"  ❤ {m.get('like_count', 0)} 💬 {m.get('comments_count', 0)} · {short(m.get('caption'))}\n  {m.get('permalink', '')}")
        if len(ranked) > 3:
            w = ranked[-1]
            lines.append(f"🔻 Eng past: {short(w.get('caption'))} (❤ {w.get('like_count', 0)})")
    else:
        lines.append("Bu hafta post chiqmagan.")

    # eng yaxshi vaqt: oxirgi postlar bo'yicha (reel/video)
    slots = {"ertalab 06–11": (6, 11), "kunduzi 11–15": (11, 15), "kechqurun 15–19": (15, 19), "oqshom 19–24": (19, 24)}
    agg = {k: [] for k in slots}
    for m in media:
        h = media_time(m).hour
        for k, (a, b) in slots.items():
            if a <= h < b:
                agg[k].append(score(m))
    rows = [(sum(v) / len(v), k, len(v)) for k, v in agg.items() if len(v) >= 3]
    if rows:
        rows.sort(reverse=True)
        lines.append(f"⏰ Eng yaxshi vaqt: {rows[0][1]} (o'rtacha {rows[0][0]:.1f} faollik, {rows[0][2]} post)")
    types = {}
    for m in media:
        types.setdefault(m.get("media_type", "?"), []).append(score(m))
    if len(types) > 1:
        t = ", ".join(f"{k} {sum(v)/len(v):.1f}" for k, v in sorted(types.items()))
        lines.append(f"📈 O'rtacha faollik: {t}")
    lines.append("Faollik = layk + 3×izoh. Ko'rishlar soni bu hisobotda yo'q.")
    notify("\n".join(lines))


# ---------- xatolik signali ----------
def alert(st):
    now = datetime.now(TZ)
    sent = st.setdefault("alerts", {})
    problems = []

    def once(key, text, hours=12):
        last = sent.get(key)
        if last and now - parse_at(last) < timedelta(hours=hours):
            return
        problems.append(text)
        sent[key] = now.isoformat(timespec="minutes")

    holat = load("reja/holat.json", {})
    sys_err = holat.get("_tizim", {}).get("xato")
    if sys_err:
        once("tizim:" + sys_err[:60], f"❌ Instagram tizimi xatosi: {sys_err[:200]}")

    ti = load("reja/token_info.json", {})
    if ti.get("valid") is False:
        once("token-invalid", "🔑 Instagram tokeni yaroqsiz! Yangi token kerak, postlar chiqmaydi.", 6)
    elif ti.get("days_left") is not None and ti["days_left"] < 7:
        once("token-soon", f"🔑 Instagram tokeni {ti['days_left']:.0f} kundan keyin tugaydi. Yangilang.", 24)

    for p in load("reja/posts.json", []):
        if p["id"].startswith("_"):
            continue
        s = holat.get(p["id"], {})
        if s.get("status") in ("chiqdi", "o'tkazildi"):
            continue
        late = now - parse_at(p["at"])
        if late < timedelta(0) or late > timedelta(hours=12):
            continue  # kelajakdagi yoki eskirgan postlar haqida signal berilmaydi
        if s.get("urinish", 0) >= 3:
            once("xato:" + p["id"], f"❌ Post chiqmadi: {p['id']}\nSabab: {str(s.get('sabab', ''))[:200]}", 24)
        elif late > timedelta(minutes=60):
            once("kech:" + p["id"], f"⏰ Post kechikyapti ({int(late.total_seconds() // 60)} daq): {p['id']}\nGitHub navbati sekin yoki xato bor. Actions bo'limini tekshiring.", 24)

    # eski kalitlarni tozalash
    for k in [k for k, v in sent.items() if now - parse_at(v) > timedelta(days=3)]:
        sent.pop(k)
    if problems:
        notify("⚠️ Metartshop agenti\n\n" + "\n\n".join(problems))
    else:
        print("Muammo yo'q.")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    mode = args[0] if args else "morning"
    st = load(STATE, {})
    {"morning": morning, "weekly": weekly, "alert": alert}[mode](st)
    save_state(st)


if __name__ == "__main__":
    main()
