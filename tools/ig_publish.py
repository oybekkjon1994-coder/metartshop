"""O'zimizning post rejalashtirgich (Metricool o'rniga, bepul).

reja/posts.json dagi vaqti kelgan postlarni Instagram Graph API orqali chiqaradi.
GitHub Actions har 15 daqiqada ishga tushiradi (.github/workflows/ig-post.yml).

Kerak: GitHub Secrets -> IG_TOKEN (Facebook sahifa tokeni, ruxsatlar:
instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement).
Ixtiyoriy: TG_TOKEN + TG_CHAT — natija haqida Telegram'ga xabar.

posts.json elementi:
  {"id": "...", "at": "2026-10-27T14:00", "type": "REEL|POST|STORY",
   "media": ["https://... .mp4/.jpg", ...], "caption": "..."}
  POST + bir nechta rasm = karusel. "media" da "repo:reels/x.mp4" yozilsa,
  shu repodagi faylning raw havolasi ishlatiladi.
Holat reja/holat.json da saqlanadi: {"id": {"status": "chiqdi|xato|o'tkazildi", ...}}
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

API = "https://graph.facebook.com/v21.0"
IG_API = "https://graph.instagram.com/v21.0"  # Instagram login tokeni (IGAA...) uchun
TZ = timezone(timedelta(hours=5))  # Asia/Samarkand
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, "reja", "posts.json")
STATE = os.path.join(ROOT, "reja", "holat.json")
MAX_LATE = timedelta(hours=float(os.environ.get("MAX_LATE_HOURS", "3")))
REPO = os.environ.get("GITHUB_REPOSITORY", "oybekkjon1994-coder/metartshop")
SHA = os.environ.get("GITHUB_SHA", "main")
DEFAULT_IG = os.environ.get("IG_DEFAULT_ID", "17841470082191241")  # @metart_shop


class ApiError(Exception):
    pass


def call(method, path, token, **params):
    params["access_token"] = token
    data = urllib.parse.urlencode(params).encode()
    url = f"{(IG_API if token.startswith('IG') else API)}/{path}"
    req = urllib.request.Request(url + ("?" + data.decode() if method == "GET" else ""),
                                 data=None if method == "GET" else data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        try: msg = json.loads(body)["error"]["message"]
        except Exception: msg = body[:300]
        raise ApiError(f"{e.code}: {msg}")


def ig_user_id(token):
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"]
    if token.startswith("IG"):  # Instagram login: hisob egasining o'zi
        return call("GET", "me", token, fields="user_id,username").get("user_id") or "me"
    try:  # sahifa tokeni bo'lsa
        me = call("GET", "me", token, fields="instagram_business_account")
        if me.get("instagram_business_account"):
            return me["instagram_business_account"]["id"]
    except ApiError:
        pass  # foydalanuvchi tokeni — bu maydon yo'q, sahifalardan qidiramiz
    try:
        pages = call("GET", "me/accounts", token, fields="instagram_business_account,name").get("data", [])
    except ApiError:
        pages = []
    for p in pages:
        if p.get("instagram_business_account"):
            return p["instagram_business_account"]["id"]
    if DEFAULT_IG: return DEFAULT_IG
    raise ApiError("Instagram biznes akkaunt topilmadi — token sahifa tokenimi va Instagram sahifaga ulanganmi?")


def media_url(m):
    if m.startswith("repo:"):
        return f"https://raw.githubusercontent.com/{REPO}/{SHA}/{m[5:]}"
    return m


def is_video(u):
    return u.split("?")[0].lower().endswith((".mp4", ".mov"))


def wait_ready(cid, token, limit=600):
    t0 = time.time()
    while time.time() - t0 < limit:
        st = call("GET", cid, token, fields="status_code,status")
        code = st.get("status_code")
        if code == "FINISHED": return
        if code in ("ERROR", "EXPIRED"): raise ApiError(f"Media tayyorlanmadi: {st.get('status')}")
        time.sleep(10)
    raise ApiError("Media 10 daqiqada tayyor bo'lmadi")


def container(ig, token, url, **extra):
    if is_video(url):
        return call("POST", f"{ig}/media", token, video_url=url, **extra)["id"]
    return call("POST", f"{ig}/media", token, image_url=url, **extra)["id"]


def publish(post, ig, token):
    urls = [media_url(m) for m in post["media"]]
    kind, cap = post.get("type", "POST").upper(), post.get("caption", "")
    if kind == "REEL":
        cid = call("POST", f"{ig}/media", token, media_type="REELS", video_url=urls[0], caption=cap, share_to_feed="true")["id"]
    elif kind == "STORY":
        extra = {"media_type": "STORIES"}
        cid = container(ig, token, urls[0], **extra)
    elif len(urls) > 1:
        kids = []
        for u in urls[:10]:
            kids.append(container(ig, token, u, is_carousel_item="true", **({"media_type": "VIDEO"} if is_video(u) else {})))
        for k in kids: wait_ready(k, token)
        cid = call("POST", f"{ig}/media", token, media_type="CAROUSEL", children=",".join(kids), caption=cap)["id"]
    else:
        cid = container(ig, token, urls[0], caption=cap, **({"media_type": "REELS"} if is_video(urls[0]) else {}))
    wait_ready(cid, token)
    res = call("POST", f"{ig}/media_publish", token, creation_id=cid)
    try:
        link = call("GET", res["id"], token, fields="permalink").get("permalink", "")
    except ApiError:
        link = ""
    return res["id"], link


def notify(text):
    tok, chat = os.environ.get("TG_TOKEN"), os.environ.get("TG_CHAT")
    if not tok or not chat: return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20)
    except Exception as e:
        print("Telegram xabar yuborilmadi:", e)


def parse_at(s):
    d = datetime.fromisoformat(s)
    return d if d.tzinfo else d.replace(tzinfo=TZ)


def due_posts(posts, state, now):
    out = []
    for p in posts:
        if p["id"].startswith("_") or state.get(p["id"], {}).get("status") in ("chiqdi", "o'tkazildi"): continue
        if state.get(p["id"], {}).get("urinish", 0) >= 3: continue
        at = parse_at(p["at"])
        if at <= now: out.append((at, p))
    return [p for _, p in sorted(out, key=lambda x: x[0])]


def main():
    dry = "--dry" in sys.argv
    posts = json.load(open(POSTS, encoding="utf-8"))
    state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    now = datetime.now(TZ)
    todo = due_posts(posts, state, now)
    if not todo:
        print("Vaqti kelgan post yo'q."); return 0
    token = os.environ.get("IG_TOKEN")
    if not token and not dry:
        state["_tizim"] = {"xato": "IG_TOKEN yo'q — GitHub Secrets ga qo'shing", "vaqt": now.isoformat(timespec="minutes")}
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("IG_TOKEN yo'q — GitHub Secrets ga qo'shing."); return 0
    try:
        ig = None if dry else ig_user_id(token)
    except ApiError as e:
        state["_tizim"] = {"xato": "Token/akkaunt: " + str(e)[:300], "vaqt": now.isoformat(timespec="minutes")}
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("Token xatosi:", e); return 0
    state.pop("_tizim", None)
    changed = False
    for p in todo:
        st = state.setdefault(p["id"], {})
        if now - parse_at(p["at"]) > MAX_LATE:
            st.update(status="o'tkazildi", sabab="vaqti o'tib ketgan", vaqt=now.isoformat(timespec="minutes"))
            print("O'tkazildi (kech):", p["id"]); changed = True; continue
        if dry:
            print("[sinov] chiqarilardi:", p["id"], p.get("type"), [media_url(m) for m in p["media"]]); continue
        try:
            mid, link = publish(p, ig, token)
            st.update(status="chiqdi", media_id=mid, link=link, vaqt=now.isoformat(timespec="minutes"))
            print("Chiqdi:", p["id"], link); notify(f"✅ Instagram'ga chiqdi: {p['id']}\n{link}")
        except ApiError as e:
            st["urinish"] = st.get("urinish", 0) + 1
            st.update(status="xato", sabab=str(e)[:300], vaqt=now.isoformat(timespec="minutes"))
            print("Xato:", p["id"], e)
            if st["urinish"] >= 3: notify(f"❌ Post chiqmadi ({p['id']}): {e}")
        changed = True
        time.sleep(5)
    if changed and not dry:
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
