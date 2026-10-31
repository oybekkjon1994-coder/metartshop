"""IG_TOKEN ning haqiqiy muddatini Meta'dan so'raydi -> reja/token_info.json"""
import os, json, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
API = "https://graph.facebook.com/v21.0"
tok = os.environ.get("IG_TOKEN", "")
q = urllib.parse.quote(tok)
out = {}
try:
    req = urllib.request.Request(f"{API}/debug_token?input_token={q}&access_token={q}",
                                 headers={"User-Agent": "metartshop"})
    d = json.load(urllib.request.urlopen(req, timeout=25)).get("data", {})
    exp = d.get("expires_at", 0)
    dexp = d.get("data_access_expires_at", 0)
    now = datetime.now(timezone.utc)
    def fmt(ts):
        if not ts:
            return "cheksiz (never)"
        dt = datetime.fromtimestamp(ts, timezone(timedelta(hours=5)))
        return dt.strftime("%Y-%m-%d %H:%M")
    def days(ts):
        return None if not ts else round((datetime.fromtimestamp(ts, timezone.utc) - now).total_seconds()/86400, 1)
    out = {
        "valid": d.get("is_valid"),
        "type": d.get("type"),
        "expires_at": fmt(exp),
        "days_left": days(exp),
        "data_access_expires_at": fmt(dexp),
        "data_access_days_left": days(dexp),
        "scopes": d.get("scopes", []),
        "tekshirildi": now.astimezone(timezone(timedelta(hours=5))).strftime("%Y-%m-%d %H:%M"),
    }
except Exception as e:
    out = {"error": str(e)[:200]}
json.dump(out, open("reja/token_info.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(out, ensure_ascii=False))
