"""Mijoz savollari (izohlardan), obunachi maqsadi/prognozi va Direct javob loyihalari. Bepul, GitHub Actions'da."""
import os, re, json, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=5))
API = "https://graph.facebook.com/v21.0"
OWN = {"metart_shop"}

INTENTS = {
    "narx": ["narx", "qancha", "necha pul", "necha so'm", "nech pul", "цена", "сколько", "стоит", "kancha", "narxi"],
    "yetkazish": ["yetkaz", "dostavka", "доставка", "viloyat", "samarqand", "buxoro", "andijon", "farg'ona", "namangan"],
    "o'lcham/rang": ["o'lcham", "razmer", "размер", "rang", "цвет", "kattaligi", "balandlik"],
    "buyurtma": ["buyurtma", "zakaz", "заказ", "olmoqchi", "olaman", "kerak", "хочу", "заказать"],
    "manzil/aloqa": ["qayerda", "manzil", "adres", "адрес", "telefon", "raqam", "номер", "nomer", "aloqa", "lichka", "direct", "директ"],
    "chegirma/to'lov": ["chegirma", "skidka", "скидка", "to'lov", "nasiya", "rassrochka", "click", "payme"],
}


SPAM = ["http", "www.", "t.me/", "wa.me", "bit.ly", "kazino", "casino", "1xbet", "melbet", "букмекер",
        "ishlab toping", "ishlab top", "daromad", "заработ", "инвест", "crypto", "kripto", "usdt", "obuna bo'ling", "follow me",
        "подпишись", "sub4sub", "like4like", "dm for", "pul ishlash"]
TOXIC = ["ahmoq", "axmoq", "yaramas", "firibgar", "aldamchi", "scam", "мошенник", "обман", "тупой", "дурак", "лох"]


def suspicious(text):
    t = (text or "").lower()
    why = []
    if any(w in t for w in SPAM):
        why.append("spam/reklama")
    if re.search(r"(\+?998[\s-]?\d{2}[\s-]?\d{3}|\b\d{9,12}\b)", t):
        why.append("telefon raqami")
    if any(w in t for w in TOXIC):
        why.append("haqoratli/shubhali")
    return why


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": "metartshop-agent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def intents_of(text):
    t = (text or "").lower()
    out = [k for k, kws in INTENTS.items() if any(w in t for w in kws)]
    if "?" in t and not out:
        out = ["boshqa savol"]
    return out


def savollar(tok, media, limit_media=25):
    """So'nggi postlar izohlaridan mijoz savollarini yig'adi. (instagram_manage_comments ruxsati bor)"""
    q = urllib.parse.urlencode({"access_token": tok})
    now = datetime.now(TZ)
    total, qs, per, flagged = 0, [], {}, []
    for m in media[:limit_media]:
        if not m.get("id") or (m.get("comments_count") or 0) == 0:
            continue
        try:
            d = get(f"{API}/{m['id']}/comments?fields=text,username,timestamp,replies.limit(1){{id}}&limit=50&{q}")
        except Exception as e:
            print("Izoh olinmadi:", str(e)[:120]); continue
        for c in d.get("data", []):
            if (c.get("username") or "").lower() in OWN:
                continue
            total += 1
            why = suspicious(c.get("text"))
            if why:
                flagged.append({"matn": re.sub(r"\s+", " ", c.get("text") or "")[:120], "sabab": why,
                                "kim": c.get("username"), "havola": m.get("permalink"), "vaqt": c.get("timestamp", "")[:10]})
            its = intents_of(c.get("text"))
            if not its:
                continue
            answered = bool((c.get("replies") or {}).get("data"))
            for i in its:
                per[i] = per.get(i, 0) + 1
            qs.append({"matn": re.sub(r"\s+", " ", c.get("text") or "")[:140], "turi": its, "javob_berilgan": answered,
                       "post": (m.get("caption") or "")[:40].replace("\n", " "), "havola": m.get("permalink"),
                       "vaqt": c.get("timestamp", "")[:10]})
    qs.sort(key=lambda x: x["vaqt"], reverse=True)
    return {"jami_izoh": total, "savol_soni": len(qs), "turlari": dict(sorted(per.items(), key=lambda x: -x[1])),
            "javobsiz": [x for x in qs if not x["javob_berilgan"]][:8], "oxirgi_savollar": qs[:5],
            "shubhali": flagged[:10], "shubhali_soni": len(flagged)}


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def maqsad(followers, hist, target=None):
    """Obunachi maqsadi: hozirgi sur'at bo'yicha prognoz va kerakli sur'at."""
    cfg = load("reja/maqsad.json", {})
    target = target or cfg.get("obunachi") or ((int(followers // 500) + 2) * 500)
    out = {"maqsad": target, "hozir": followers, "qoldi": target - followers}
    if hist and len(hist) >= 2:
        ks = sorted(hist)[-30:]
        d0 = datetime.strptime(ks[0], "%Y-%m-%d"); d1 = datetime.strptime(ks[-1], "%Y-%m-%d")
        days = max((d1 - d0).days, 1)
        out["tarix_kun"] = days
        if days >= 7:  # kam kunlik tarixdan prognoz chiqarmaymiz
            rate = (hist[ks[-1]] - hist[ks[0]]) / days
            out["kunlik_osish"] = round(rate, 2)
            if rate > 0:
                out["yetish_kun"] = round((target - followers) / rate)
    out["30_kunda_uchun_kerak_kunlik"] = round(max(target - followers, 0) / 30, 1)
    return out


def matn_savollar(s):
    if not s:
        return ""
    L = [f"💬 Mijoz savollari (izohlardan): {s['jami_izoh']} ta izoh, {s['savol_soni']} tasi savol"]
    if s["turlari"]:
        L.append("Eng ko'p so'ralgan: " + ", ".join(f"{k} ({v})" for k, v in list(s["turlari"].items())[:4]))
        L.append(f"👉 Keyingi video/post: '{list(s['turlari'])[0]}' haqida javob bering")
    if s["javobsiz"]:
        L.append("Javobsiz savollar:")
        for x in s["javobsiz"][:5]:
            L.append(f"• {x['vaqt']} · {x['matn']}")
    return "\n".join(L)


def matn_shubhali(s):
    if not s or not s.get("shubhali_soni"):
        return ""
    L = [f"🚩 Shubhali izohlar: {s['shubhali_soni']} ta (o'chirish/yashirishni o'zingiz hal qiling)"]
    for x in s["shubhali"][:5]:
        L.append(f"• @{x['kim']} · {', '.join(x['sabab'])} · {x['matn'][:70]}")
    return "\n".join(L)


def raqobatchilar(tok, uid, own_followers=None):
    """Raqobatchi akkauntlar (reja/raqobatchi.json): business_discovery orqali ochiq statistika."""
    names = load("reja/raqobatchi.json", {}).get("akkauntlar", [])
    if not names or not uid:
        return {"akkauntlar": []}
    q = urllib.parse.urlencode({"access_token": tok})
    now = datetime.now(TZ)
    out = []
    for nm in names[:5]:
        f = ("business_discovery.username(%s){followers_count,media_count,"
             "media.limit(30){caption,like_count,comments_count,timestamp,media_type,permalink}}" % nm)
        try:
            d = get(f"{API}/{uid}?fields={urllib.parse.quote(f, safe='(){},.')}&{q}")["business_discovery"]
        except Exception as e:
            out.append({"nom": nm, "xato": "ochib bo'lmadi (shaxsiy akkaunt yoki mavjud emas)"})
            continue
        ms = (d.get("media") or {}).get("data", [])
        def age(m):
            try:
                return (now - datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(TZ)).days
            except Exception:
                return 999
        r30 = [m for m in ms if age(m) <= 30]
        sc = lambda m: (m.get("like_count") or 0) + 3 * (m.get("comments_count") or 0)
        top = sorted(ms, key=sc, reverse=True)[:2]
        out.append({"nom": nm, "obunachi": d.get("followers_count"), "post_soni": d.get("media_count"),
                    "oxirgi_30_kun_post": len(r30),
                    "ortacha_layk": round(sum((m.get("like_count") or 0) for m in ms) / len(ms), 1) if ms else 0,
                    "top": [{"matn": re.sub(r"\s+", " ", m.get("caption") or "")[:70], "layk": m.get("like_count") or 0,
                             "izoh": m.get("comments_count") or 0, "havola": m.get("permalink")} for m in top]})
    return {"akkauntlar": out, "bizning_obunachi": own_followers}


def matn_raqobat(r):
    if not r or not r.get("akkauntlar"):
        return "🕵️ Raqobatchi tahlili: akkauntlar kiritilmagan. Issue sarlavhasi: 'raqobatchi nom1 nom2'."
    L = ["🕵️ Raqobatchilar:"]
    for a in r["akkauntlar"]:
        if a.get("xato"):
            L.append(f"• @{a['nom']}: {a['xato']}"); continue
        L.append(f"• @{a['nom']}: {a['obunachi']} obunachi, oxirgi 30 kunda {a['oxirgi_30_kun_post']} post, o'rtacha ❤ {a['ortacha_layk']}")
        for t in a["top"]:
            L.append(f"   ↳ ❤ {t['layk']} 💬 {t['izoh']} · {t['matn']}")
    return "\n".join(L)


def matn_maqsad(m):
    if not m:
        return ""
    L = [f"🎯 Maqsad: {m['maqsad']} obunachi (hozir {m['hozir']}, {m['qoldi']} qoldi)"]
    if m.get("yetish_kun"):
        L.append(f"Hozirgi sur'at (kuniga {m['kunlik_osish']:+}) bilan taxminan {m['yetish_kun']} kunda yetasiz")
    elif m.get("kunlik_osish") is not None:
        L.append(f"Hozir obunachi o'smayapti (kuniga {m['kunlik_osish']:+}, {m['tarix_kun']} kun tarixi)")
    else:
        L.append(f"Prognoz uchun kamida 7 kunlik obunachi tarixi kerak (hozir {m.get('tarix_kun', 0)} kun, har kuni yig'iladi)")
    L.append(f"30 kunda yetish uchun kuniga +{m['30_kunda_uchun_kerak_kunlik']} obunachi kerak")
    return "\n".join(L)


# ---------- Direct savoli uchun javob loyihasi ----------
JAVOB = {
    "narx": "Assalomu alaykum! Narx o'lcham va materialga bog'liq. Chizma yoki o'lchamni yuborsangiz, tez hisoblab beramiz. "
            "Lazer kesish uchun faylni (DXF/CDR/SVG) @lazer_uz77_bot ga yuboring, narx darhol chiqadi. 🙌",
    "yetkazish": "Toshkent bo'ylab Yandex orqali, viloyatlarga BTS pochta orqali yetkazib beramiz. Qaysi shaharga kerak? 🚚",
    "o'lcham/rang": "O'lcham va rangni o'zingiz tanlaysiz, buyurtma asosida tayyorlaymiz. Kerakli o'lcham va rangni yozing, narxini aytamiz.",
    "buyurtma": "Buyurtma uchun nima kerakligini va o'lchamini yozing yoki @Metart_shop_bot ga kiring. Tez javob beramiz! 🔩",
    "manzil/aloqa": "Biz Toshkentdamiz. Buyurtma va savollar uchun Telegram: @lazekametal yoki shu yerga yozing. 📩",
    "chegirma/to'lov": "Ko'p miqdordagi buyurtmalarga chegirma bor. Nima va qancha kerakligini yozing, eng yaxshi narxni aytamiz.",
    "boshqa savol": "Assalomu alaykum! Savolingizni batafsilroq yozing, albatta yordam beramiz. 🙌",
}


def javob_loyiha(savol):
    its = intents_of(savol) or ["boshqa savol"]
    parts = []
    for i in its[:3]:
        parts.append(JAVOB[i])
    base = "\n\n".join(parts)
    key = os.environ.get("GROQ_API_KEY")
    if key:
        try:
            body = json.dumps({"model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"), "temperature": 0.4, "max_tokens": 500,
                               "messages": [{"role": "system", "content": "Sen metall buyumlar va lazer kesish ustaxonasi sotuvchisisan. Mijozga Instagram Direct'da qisqa, samimiy, o'zbek tilida (lotin) javob yoz. Faqat berilgan faktlardan foydalan, narx uydirma, mijoz tilida (ruscha so'rasa ruscha) yoz. 1–3 gap."},
                                            {"role": "user", "content": f"Mijoz savoli: {savol}\n\nFaktlar:\n{base}"}]}).encode()
            req = urllib.request.Request("https://api.groq.com/openai/v1/chat/completions", data=body,
                                         headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "metartshop-agent/1.0"})
            r = json.load(urllib.request.urlopen(req, timeout=40))
            return r["choices"][0]["message"]["content"].strip(), "AI (Groq)"
        except Exception as e:
            print("Groq xato:", str(e)[:150])
    return base, "shablon"
