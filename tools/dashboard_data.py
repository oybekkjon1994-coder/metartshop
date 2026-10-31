"""Boshqaruv paneli uchun ma'lumot yig'adi -> reja/dashboard.json.
Dollar, ob-havo, Instagram (obunachi + oxirgi postlar), bugungi va keyingi postlar.
GitHub Actions'da ishlaydi (bepul). Telegram kerak emas."""
import os, json, urllib.request, urllib.parse, urllib.error
from datetime import datetime, timedelta, timezone

TZ = timezone(timedelta(hours=5))
NOW = datetime.now(TZ)
API = "https://graph.facebook.com/v21.0"


def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": "metartshop"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")[:200]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body}")


def dollar():
    # 1) CBU (rasmiy kurs, Diff bilan) -> 2) open.er-api (ishonchli zaxira)
    for url in ["https://cbu.uz/uz/arkhiv-kursov-valyut/json/USD/"]:
        try:
            u = get(url, timeout=10)[0]
            return {"rate": round(float(u["Rate"])), "diff": round(float(u.get("Diff") or 0)), "manba": "CBU"}
        except Exception:
            pass
    try:
        d = get("https://open.er-api.com/v6/latest/USD", timeout=12)
        uzs = d.get("rates", {}).get("UZS")
        if uzs:
            return {"rate": round(float(uzs)), "diff": 0, "manba": "bozor"}
    except Exception as e:
        return {"error": str(e)[:80]}
    return {"error": "manbalar javob bermadi"}


WCODE = {0: "Ochiq", 1: "Asosan ochiq", 2: "Bulutli", 3: "To'liq bulutli",
         45: "Tuman", 48: "Tuman", 51: "Mayda yomg'ir", 53: "Yomg'ir", 55: "Yomg'ir",
         61: "Yomg'ir", 63: "Yomg'ir", 65: "Kuchli yomg'ir", 71: "Qor", 73: "Qor",
         75: "Kuchli qor", 80: "Jala", 81: "Jala", 82: "Kuchli jala",
         95: "Momaqaldiroq", 96: "Momaqaldiroq"}


def obhavo():
    try:
        d = get("https://api.open-meteo.com/v1/forecast?latitude=41.31&longitude=69.24"
                "&current=temperature_2m,weather_code&daily=temperature_2m_max,temperature_2m_min"
                "&timezone=Asia/Tashkent")
        c = d["current"]
        return {"temp": round(c["temperature_2m"]), "desc": WCODE.get(c.get("weather_code"), ""),
                "hi": round(d["daily"]["temperature_2m_max"][0]),
                "lo": round(d["daily"]["temperature_2m_min"][0])}
    except Exception as e:
        return {"error": str(e)[:80]}


def instagram():
    tok = os.environ.get("IG_TOKEN")
    ig = os.environ.get("IG_USER_ID") or os.environ.get("IG_DEFAULT_ID", "17841470082191241")
    out = {"username": "metart_shop", "followers": None, "media_count": None, "posts": []}
    if tok:
        q = urllib.parse.quote(tok)
        try:
            a = get(f"{API}/{ig}?fields=username,followers_count,media_count&access_token={q}")
            out["username"] = a.get("username", "metart_shop")
            out["followers"] = a.get("followers_count")
            out["media_count"] = a.get("media_count")
        except Exception as e:
            out["error"] = str(e)[:100]
        try:
            m = get(f"{API}/{ig}/media?fields=caption,like_count,comments_count,media_type,permalink,timestamp&limit=6&access_token={q}")
            for p in m.get("data", []):
                cap = (p.get("caption") or "").split("\n")[0][:40]
                out["posts"].append({"caption": cap, "like": p.get("like_count", 0),
                                     "comment": p.get("comments_count", 0),
                                     "type": p.get("media_type", ""), "link": p.get("permalink", ""),
                                     "ts": p.get("timestamp", "")[:10]})
        except Exception:
            pass
    return out


def postlar():
    bugun = NOW.strftime("%Y-%m-%d")
    try:
        d = json.load(open("reja/posts.json", encoding="utf-8"))
        holat = {}
        try:
            holat = json.load(open("reja/holat.json", encoding="utf-8"))
        except Exception:
            pass
        posts = d if isinstance(d, list) else d.get("posts", [])
        posts = [p for p in posts if not str(p.get("id", "")).startswith("_")]
        posts.sort(key=lambda p: p.get("at", ""))

        def info(p):
            st = holat.get(p["id"], {}).get("status", "")
            return {"id": p["id"], "at": p.get("at", ""),
                    "type": p.get("type", ""), "status": st}

        today = [info(p) for p in posts if str(p.get("at", "")).startswith(bugun)]
        keyingi = [info(p) for p in posts if p.get("at", "") > NOW.strftime("%Y-%m-%dT%H:%M")][:6]
        # kecha chiqqan
        kecha = (NOW - timedelta(days=1)).strftime("%Y-%m-%d")
        kecha_n = sum(1 for k, v in holat.items()
                      if isinstance(v, dict) and v.get("status") == "chiqdi"
                      and str(v.get("vaqt", "")).startswith(kecha))
        return today, keyingi, kecha_n
    except Exception:
        return [], [], 0


def main():
    today, keyingi, kecha_n = postlar()
    ig = instagram()
    # So'rov xato bersa — oxirgi to'g'ri Instagram raqamlarini saqlab qolamiz
    if not ig.get("followers"):
        try:
            eski = json.load(open("reja/dashboard.json", encoding="utf-8")).get("instagram", {})
            if eski.get("followers"):
                xato = ig.get("error")
                ig = eski
                ig["stale"] = True
                if xato:
                    ig["last_error"] = xato
        except Exception:
            pass
    data = {
        "updated": NOW.strftime("%Y-%m-%d %H:%M"),
        "dollar": dollar(),
        "obhavo": obhavo(),
        "instagram": ig,
        "kecha_chiqdi": kecha_n,
        "bugun_postlar": today,
        "keyingi_postlar": keyingi,
    }
    os.makedirs("reja", exist_ok=True)
    json.dump(data, open("reja/dashboard.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("dashboard.json yozildi:", data["updated"])


if __name__ == "__main__":
    main()
