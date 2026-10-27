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

def ig_id():
    if os.environ.get("IG_USER_ID"): return os.environ["IG_USER_ID"]
    if tok.startswith("IG"): return call("me", fields="user_id")["user_id"]
    me = call("me", fields="instagram_business_account")
    if me.get("instagram_business_account"): return me["instagram_business_account"]["id"]
    for pg in call("me/accounts", fields="instagram_business_account").get("data", []):
        if pg.get("instagram_business_account"): return pg["instagram_business_account"]["id"]
    raise SystemExit("IG akkaunt topilmadi")

ig = ig_id()
acc = call(ig, fields="username,name,followers_count,follows_count,media_count")
media = call(f"{ig}/media", fields="id,caption,media_type,timestamp,like_count,comments_count,permalink", limit="12").get("data", [])
for m in media:
    try:
        ins = call(f"{m['id']}/insights", metric="reach").get("data", [])
        m["reach"] = ins[0]["values"][0]["value"] if ins else None
    except Exception:
        m["reach"] = None
    m["caption"] = (m.get("caption") or "").split("\n")[0][:60]

out = {"vaqt": datetime.now(TZ).isoformat(timespec="minutes"), "akkaunt": acc, "postlar": media}
json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(acc, ensure_ascii=False))
