"""Instagram akkaunt holati — followers, postlar, oxirgi postlar faolligi.
GitHub Actions ichida IG_TOKEN bilan ishlaydi, natijani reja/ig-stat.json ga yozadi."""
import json, os, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta

API = "https://graph.facebook.com/v21.0"
IG_API = "https://graph.instagram.com/v21.0"
TZ = timezone(timedelta(hours=5))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "reja", "ig-stat.json")
tok = os.environ["IG_TOKEN"]
base = IG_API if tok.startswith("IG") else API

def call(path, **p):
    p["access_token"] = tok
    url = f"{base}/{path}?" + urllib.parse.urlencode(p)
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())

DEFAULT_IG = "17841470082191241"  # @metart_shop
def ig_id():
    if os.environ.get("IG_USER_ID"): return os.environ["IG_USER_ID"]
    if tok.startswith("IG"):
        try: return call("me", fields="user_id")["user_id"]
        except Exception: return DEFAULT_IG
    try:
        me = call("me", fields="instagram_business_account")
        if me.get("instagram_business_account"): return me["instagram_business_account"]["id"]
    except Exception: pass
    try:
        for pg in call("me/accounts", fields="instagram_business_account").get("data", []):
            if pg.get("instagram_business_account"): return pg["instagram_business_account"]["id"]
    except Exception: pass
    return DEFAULT_IG

def safe_call(path, **p):
    try: return call(path, **p), None
    except urllib.error.HTTPError as e:
        try: msg = json.loads(e.read())["error"]["message"]
        except Exception: msg = str(e)
        return None, f"{e.code}: {msg}"
    except Exception as e:
        return None, str(e)

out = {"vaqt": datetime.now(TZ).isoformat(timespec="minutes")}
try:
    ig = ig_id()
    out["ig_id"] = ig
    acc, err = safe_call(ig, fields="username,name,followers_count,follows_count,media_count")
    if acc is None:
        acc, err2 = safe_call(ig, fields="username,followers_count,media_count")
        if acc is None: out["xato_akkaunt"] = err
    out["akkaunt"] = acc or {}
    media_r, err = safe_call(f"{ig}/media", fields="id,caption,media_type,timestamp,like_count,comments_count,permalink", limit="12")
    media = (media_r or {}).get("data", [])
    if media_r is None: out["xato_media"] = err
    for m in media:
        ins, _ = safe_call(f"{m['id']}/insights", metric="reach")
        m["reach"] = (ins or {}).get("data", [{}])[0].get("values", [{}])[0].get("value") if ins else None
        m["caption"] = (m.get("caption") or "").split("\n")[0][:60]
    out["postlar"] = media
except Exception as e:
    import traceback; out["xato"] = traceback.format_exc()[-800:]
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out.get("akkaunt") or out, ensure_ascii=False)[:500])
