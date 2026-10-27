"""ig_publish.py ni soxta API bilan sinash: REEL, STORY, karusel, kechikkan post."""
import json, os, sys, tempfile
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "tools"))
import ig_publish as P

calls = []
def fake(method, path, token, **kw):
    calls.append((method, path, kw))
    if path == "me": return {"instagram_business_account": {"id": "IG1"}}
    if path.endswith("/media"): return {"id": f"C{len(calls)}"}
    if path.endswith("/media_publish"): return {"id": "M" + kw["creation_id"]}
    if kw.get("fields") == "status_code,status": return {"status_code": "FINISHED"}
    if kw.get("fields") == "permalink": return {"permalink": "https://instagram.com/p/x"}
    raise AssertionError(path)
P.call = fake; P.time.sleep = lambda s: None

d = tempfile.mkdtemp(); P.POSTS = os.path.join(d, "p.json"); P.STATE = os.path.join(d, "s.json")
now = datetime.now(P.TZ)
fmt = lambda t: t.strftime("%Y-%m-%dT%H:%M")
posts = [
    {"id": "reel", "at": fmt(now - timedelta(minutes=5)), "type": "REEL", "media": ["repo:reels/a.mp4"], "caption": "salom"},
    {"id": "story", "at": fmt(now - timedelta(minutes=5)), "type": "STORY", "media": ["https://x/s.jpeg"]},
    {"id": "karusel", "at": fmt(now - timedelta(minutes=5)), "type": "POST", "media": ["https://x/1.jpg", "https://x/2.jpg"], "caption": "k"},
    {"id": "kech", "at": fmt(now - timedelta(hours=5)), "type": "REEL", "media": ["https://x/b.mp4"]},
    {"id": "kelajak", "at": fmt(now + timedelta(hours=1)), "type": "REEL", "media": ["https://x/c.mp4"]},
]
json.dump(posts, open(P.POSTS, "w"))
os.environ["IG_TOKEN"] = "t"; os.environ.pop("IG_USER_ID", None)
assert P.main() == 0
s = json.load(open(P.STATE))
assert s["reel"]["status"] == "chiqdi" and s["story"]["status"] == "chiqdi" and s["karusel"]["status"] == "chiqdi", s
assert s["kech"]["status"] == "o'tkazildi" and "kelajak" not in s, s
reel = [c for c in calls if c[2].get("media_type") == "REELS"][0]
assert reel[2]["video_url"].startswith("https://raw.githubusercontent.com/") and reel[2]["caption"] == "salom"
assert any(c[2].get("media_type") == "STORIES" and c[2].get("image_url") for c in calls)
car = [c for c in calls if c[2].get("media_type") == "CAROUSEL"][0]
assert len(car[2]["children"].split(",")) == 2
calls.clear(); assert P.main() == 0 and not [c for c in calls if "media" in c[1]], "qayta chiqarmasligi kerak"
print("ig_publish: hammasi to'g'ri")
