"""Instagram to'liq tahlil agenti (@metart_shop) — Claude limitiga bog'liq emas, GitHub Actions'da bepul ishlaydi.

Buyruq bilan ishga tushadi (GitHub: Actions -> "Instagram tahlil" -> Run workflow, yoki repoda
sarlavhasi "tahlil" bo'lgan Issue ochish). Natija: reja/tahlil.json (panelda ko'rinadi) + Telegram.

Ma'lumot: Instagram API'dagi layk, izoh, turi, vaqti, izoh matni + obunachi tarixi.
(Ko'rishlar/reach/saqlashlar uchun token'da instagram_manage_insights ruxsati kerak — hozir yo'q.)
Matnni tuzish: agar GROQ_API_KEY secret bo'lsa, Groq (bepul) o'zbekcha tahlil yozadi; bo'lmasa qoidaviy tahlil.

  python tools/tahlil.py [--dry] [--local]
"""
import os, sys, json, re, statistics, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=5))
API = "https://graph.facebook.com/v21.0"
OUT = "reja/tahlil.json"
HIST = "reja/ig-tarix.json"
DRY = "--dry" in sys.argv
LOCAL = "--local" in sys.argv

GROUPS = {
    "Real Madrid": ["real", "madrid", "ronaldo", "halamadrid"],
    "Barselona/Messi": ["barsa", "barselona", "barcelona", "messi"],
    "Manchester": ["manchester", "manu", "man united", "man city", "siti", "united"],
    "Chelsi/Liverpul/Arsenal": ["chelsea", "chelsi", "liverpool", "liverpul", "arsenal"],
    "Soat": ["soat", "часы"],
    "Stelaj/polka": ["stelaj", "polka", "javon", "стеллаж"],
    "Veshalka/gul stend": ["veshalka", "gul stend", "stend", "вешалка"],
    "Lazer xizmati": ["lazer kesish", "lazer rezka", "kesish", "dxf", "chizma"],
    "Sovg'a": ["sovg'a", "sovga", "подарок"],
    "Konkurs/izoh so'rash": ["izohga yoz", "izoh yoz", "yut", "konkurs", "sovrin"],
    "Hayvon/yumor": ["it ", "mushuk", "hayvon", "kulgi", "🤣", "😂"],
    "Narx": ["narx", "so'm", "цена"],
}


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "metartshop-agent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def fetch():
    """Instagram'dan barcha (oxirgi ~120 ta) postlar + obunachi."""
    if LOCAL:
        d = load("reja/ig-stat.json", {})
        ms = [{"caption": p.get("caption"), "like_count": p.get("like_count", 0),
               "comments_count": p.get("comments_count", 0), "media_type": p.get("media_type", "VIDEO"),
               "timestamp": p.get("timestamp"), "permalink": p.get("permalink")} for p in d.get("postlar", [])]
        return d.get("akkaunt", {}).get("followers_count"), ms
    tok = os.environ.get("IG_TOKEN")
    if not tok:
        raise SystemExit("IG_TOKEN yo'q")
    q = urllib.parse.urlencode({"access_token": tok})
    uid = os.environ.get("IG_USER_ID", "").strip()
    if not uid:
        pages = get(f"{API}/me/accounts?fields=instagram_business_account&{q}")["data"]
        uid = next(p["instagram_business_account"]["id"] for p in pages if p.get("instagram_business_account"))
    acc = get(f"{API}/{uid}?fields=followers_count,media_count&{q}")
    url = (f"{API}/{uid}/media?fields=caption,like_count,comments_count,media_type,media_product_type,"
           f"permalink,timestamp&limit=50&{q}")
    media = []
    for _ in range(3):
        d = get(url)
        media += d.get("data", [])
        url = d.get("paging", {}).get("next")
        if not url:
            break
    return acc.get("followers_count"), media


def ts(m):
    return datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(TZ)


def sc(m):
    return (m.get("like_count") or 0) + 3 * (m.get("comments_count") or 0)


def kind(m):
    if m.get("media_product_type") == "REELS" or m.get("media_type") == "VIDEO":
        return "Reel/video"
    return {"CAROUSEL_ALBUM": "Karusel", "IMAGE": "Rasm"}.get(m.get("media_type"), m.get("media_type") or "?")


def short(s, n=45):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s if len(s) <= n else s[:n - 1] + "…"


def avg(v):
    return round(sum(v) / len(v), 1) if v else 0


def analyze(followers, media):
    now = datetime.now(TZ)
    media = [m for m in media if m.get("timestamp")]
    media.sort(key=ts, reverse=True)
    n = len(media)
    st = {"n": n, "followers": followers}
    if not n:
        return st
    st["davr"] = f"{ts(media[-1]).strftime('%d.%m')}–{ts(media[0]).strftime('%d.%m.%Y')}"
    likes = [m.get("like_count") or 0 for m in media]
    comm = [m.get("comments_count") or 0 for m in media]
    st["avg_like"], st["avg_izoh"] = avg(likes), avg(comm)
    st["median_like"] = statistics.median(likes)
    st["izohli_postlar_%"] = round(100 * sum(1 for c in comm if c) / n)
    if followers:
        st["faollik_%_obunachiga"] = round(100 * avg([sc(m) for m in media]) / followers, 2)

    # turlar
    by = {}
    for m in media:
        by.setdefault(kind(m), []).append(sc(m))
    st["turlar"] = {k: {"soni": len(v), "ortacha": avg(v)} for k, v in by.items()}

    # oylar bo'yicha (rejim o'zgarishini ko'rish uchun)
    months = {}
    for m in media:
        months.setdefault(ts(m).strftime("%Y-%m"), []).append(sc(m))
    st["oylar"] = {k: {"soni": len(v), "ortacha": avg(v)} for k, v in sorted(months.items())[-6:]}

    # mavzu/vaqt/xususiyat: oxirgi 45 kun (bir xil davr, eski mashhur postlar aralashib ketmasin)
    recent = [m for m in media if now - ts(m) <= timedelta(days=45)]
    base = recent if len(recent) >= 15 else media
    st["tahlil_oynasi"] = f"oxirgi 45 kun, {len(base)} post" if base is recent else f"barcha {len(base)} post"
    media_all, media = media, base
    n_all = n
    n = len(base)

    # mavzular
    topics = {}
    for g, kws in GROUPS.items():
        v = [sc(m) for m in media if any(k in (m.get("caption") or "").lower() for k in kws)]
        if len(v) >= 2:
            topics[g] = {"soni": len(v), "ortacha": avg(v)}
    st["mavzular"] = dict(sorted(topics.items(), key=lambda x: -x[1]['ortacha']))

    # vaqt
    slots = {"06–11": (6, 11), "11–15": (11, 15), "15–19": (15, 19), "19–24": (19, 24)}
    sv = {k: [sc(m) for m in media if a <= ts(m).hour < b] for k, (a, b) in slots.items()}
    st["soat_oralig'i"] = {k: {"soni": len(v), "ortacha": avg(v)} for k, v in sv.items() if len(v) >= 3}
    days = ["du", "se", "chor", "pay", "ju", "sha", "yak"]
    dv = {d: [sc(m) for m in media if ts(m).weekday() == i] for i, d in enumerate(days)}
    st["hafta_kuni"] = {k: {"soni": len(v), "ortacha": avg(v)} for k, v in dv.items() if len(v) >= 3}

    # izoh matni xususiyatlari
    def feat(name, pred):
        a = [sc(m) for m in media if pred(m)]
        b = [sc(m) for m in media if not pred(m)]
        if len(a) >= 3 and len(b) >= 3:
            st.setdefault("xususiyat", {})[name] = {"bor": avg(a), "yoq": avg(b), "soni(bor)": len(a)}
    cap = lambda m: (m.get("caption") or "")
    feat("izoh yozishga chaqiriq", lambda m: any(k in cap(m).lower() for k in ["izohga", "izoh yoz", "yoz!"]))
    feat("savol (?) bor", lambda m: "?" in cap(m))
    feat("bot havolasi", lambda m: "bot" in cap(m).lower())
    feat("uzun izoh (400+ belgi)", lambda m: len(cap(m)) > 400)
    feat("10+ hashtag", lambda m: cap(m).count("#") >= 10)

    media, n = media_all, n_all
    # dinamika: oxirgi 14 kun va undan oldingi 14 kun
    r = [sc(m) for m in media if now - ts(m) <= timedelta(days=14)]
    p = [sc(m) for m in media if timedelta(days=14) < now - ts(m) <= timedelta(days=28)]
    st["dinamika"] = {"oxirgi_14_kun": {"post": len(r), "ortacha": avg(r)},
                      "undan_oldingi_14_kun": {"post": len(p), "ortacha": avg(p)}}
    span = max((ts(media[0]) - ts(media[-1])).days, 1)
    st["postlar_haftasiga"] = round(n / span * 7, 1)

    top = sorted(media, key=sc, reverse=True)
    st["top5"] = [{"matn": short(m.get("caption")), "layk": m.get("like_count") or 0,
                   "izoh": m.get("comments_count") or 0, "tur": kind(m), "havola": m.get("permalink")} for m in top[:5]]
    st["past5"] = [{"matn": short(m.get("caption")), "layk": m.get("like_count") or 0,
                    "izoh": m.get("comments_count") or 0, "tur": kind(m)} for m in top[-5:]]

    # obunachi tarixi
    h = load(HIST, {})
    if h:
        ks = sorted(h)
        st["obunachi_tarixi"] = {"boshi": {ks[0]: h[ks[0]]}, "oxiri": {ks[-1]: h[ks[-1]]},
                                 "ozgarish": h[ks[-1]] - h[ks[0]], "kun": len(ks)}
    return st


def qoidaviy_matn(st):
    if not st.get("n"):
        return "Tahlil uchun post topilmadi."
    L = [f"📊 Instagram tahlili · {st['davr']} · {st['n']} ta post · {st.get('followers', '?')} obunachi", ""]
    L.append(f"O'rtacha: ❤ {st['avg_like']} layk, 💬 {st['avg_izoh']} izoh (median layk {st['median_like']}). "
             f"Postlarning {st['izohli_postlar_%']}% ida izoh bor. Haftasiga ~{st['postlar_haftasiga']} post.")
    d = st["dinamika"]
    a, b = d["oxirgi_14_kun"], d["undan_oldingi_14_kun"]
    if b["post"]:
        tr = "oshgan 📈" if a['ortacha'] > b['ortacha'] else "tushgan 📉" if a['ortacha'] < b['ortacha'] else "o'zgarmagan"
        L.append(f"Dinamika: oxirgi 14 kunda faollik {a['ortacha']} (undan oldin {b['ortacha']}), {tr}.")
    om = st.get("oylar", {})
    if len(om) >= 2:
        L.append("Oylar bo'yicha o'rtacha faollik: " + ", ".join(f"{k}: {v['ortacha']} ({v['soni']} post)" for k, v in om.items()))
        ks = list(om)
        if om[ks[-2]]["ortacha"] > 0 and om[ks[-1]]["ortacha"] < 0.4 * om[ks[-2]]["ortacha"]:
            L.append(f"🚨 Faollik keskin tushgan: {ks[-2]} da {om[ks[-2]]['ortacha']}, {ks[-1]} da {om[ks[-1]]['ortacha']}. Sababini izlang (post turi, mavzu, ko'p post, algoritm).")
    L.append(f"(Mavzu/vaqt/xususiyat tahlili: {st.get('tahlil_oynasi')})")
    L.append("")
    good, bad = [], []
    if st.get("mavzular"):
        items = list(st["mavzular"].items())
        good.append(f"Eng yaxshi mavzu: {items[0][0]} (o'rtacha {items[0][1]['ortacha']}, {items[0][1]['soni']} post)")
        if len(items) > 2:
            bad.append(f"Eng past mavzu: {items[-1][0]} (o'rtacha {items[-1][1]['ortacha']})")
    t = st["turlar"]
    if len(t) > 1:
        bt = max(t.items(), key=lambda x: x[1]['ortacha'])
        good.append(f"Eng yaxshi format: {bt[0]} (o'rtacha {bt[1]['ortacha']})")
    if st.get("soat_oralig'i"):
        bs = max(st["soat_oralig'i"].items(), key=lambda x: x[1]['ortacha'])
        ws = min(st["soat_oralig'i"].items(), key=lambda x: x[1]['ortacha'])
        good.append(f"Eng yaxshi vaqt: {bs[0]} soat (o'rtacha {bs[1]['ortacha']})")
        if ws[0] != bs[0]:
            bad.append(f"Eng past vaqt: {ws[0]} soat (o'rtacha {ws[1]['ortacha']})")
    for k, v in st.get("xususiyat", {}).items():
        if v["bor"] > v['yoq'] * 1.3:
            good.append(f"{k}: bor bo'lsa {v['bor']}, yo'q bo'lsa {v['yoq']} — yaxshi ishlayapti")
        elif v["bor"] < v['yoq'] * 0.7:
            bad.append(f"{k}: bor bo'lsa {v['bor']}, yo'q bo'lsa {v['yoq']} — kamaytiring")
    if st["avg_izoh"] < 0.3:
        bad.append("Izohlar juda kam — odamlar ko'rib, gaplashmayapti")
    L.append("✅ Yaxshi ketyapti:")
    L += ["• " + x for x in good] or ["• hali aniq xulosa uchun ma'lumot yetmaydi"]
    L.append("")
    L.append("⚠️ Yaxshi emas:")
    L += ["• " + x for x in bad] or ["• sezilarli muammo topilmadi"]
    L.append("")
    L.append("🏆 Eng yaxshi postlar:")
    for m in st["top5"][:3]:
        L.append(f"• ❤ {m['layk']} 💬 {m['izoh']} · {m['tur']} · {m['matn']}")
    L.append("🔻 Eng past postlar:")
    for m in st["past5"][:3]:
        L.append(f"• ❤ {m['layk']} 💬 {m['izoh']} · {m['tur']} · {m['matn']}")
    if st.get("obunachi_tarixi"):
        o = st["obunachi_tarixi"]
        L += ["", f"👥 Obunachi: {o['kun']} kun ichida {o['ozgarish']:+d}"]
    L += ["", "ℹ️ Ko'rishlar/reach/saqlashlar bu tahlilda yo'q (Instagram ruxsati kerak)."]
    return "\n".join(L)


def groq_matn(st):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    system = ("Sen metall buyumlar (lazer kesish, soat, stelaj, skameyka) sotadigan Instagram do'konining tahlilchisisan. "
              "Faqat o'zbek tilida (lotin) yoz. Faqat berilgan raqamlarga tayan, hech narsa o'ylab topma. "
              "Qisqa va aniq yoz, telefonda o'qiladigan bo'lsin. Tuzilishi: 1) Umumiy holat (2-3 gap), "
              "2) ✅ Nima yaxshi ketyapti (raqamlar bilan), 3) ⚠️ Nima ishlamayapti (raqamlar bilan), "
              "4) 🎯 Keyingi 7 kun uchun 5 ta aniq qadam. Ko'rishlar (reach) ma'lumoti yo'qligini bir marta eslat.")
    body = json.dumps({"model": model, "temperature": 0.3, "max_tokens": 1400,
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": "Statistika (JSON):\n" + json.dumps(st, ensure_ascii=False)}]}).encode()
    req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body,
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                                          "User-Agent": "metartshop-agent/1.0"})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=60))
        return r["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("Groq xato:", str(e)[:200])
        return None


def notify(text):
    print("----- XABAR -----\n" + text + "\n-----------------")
    tok, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if DRY or not tok or not chat:
        return
    for i in range(0, len(text), 3800):
        try:
            data = urllib.parse.urlencode({"chat_id": chat, "text": text[i:i + 3800],
                                           "disable_web_page_preview": "true"}).encode()
            urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20)
        except Exception as e:
            print("Telegram xato:", e)


def main():
    followers, media = fetch()
    now = datetime.now(TZ)
    if followers and not DRY and not LOCAL:  # obunachi tarixi (kuniga bitta nuqta)
        h = load(HIST, {})
        h[now.strftime("%Y-%m-%d")] = followers
        json.dump(dict(sorted(h.items())[-400:]), open(HIST, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    st = analyze(followers, media)
    base = qoidaviy_matn(st)
    ai = groq_matn(st) if st.get("n") else None
    matn = ("🤖 " + ai) if ai else base
    out = {"vaqt": now.strftime("%Y-%m-%d %H:%M"), "manba": "groq" if ai else "qoidaviy", "matn": matn,
           "qoidaviy": base, "stat": st}
    if not DRY:
        json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    notify(matn)


if __name__ == "__main__":
    main()
