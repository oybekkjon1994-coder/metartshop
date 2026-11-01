"""Issue orqali buyruqlar (faqat repo egasi): 'javob ...', 'maqsad 6500', 'raqobatchi nom1 nom2'.
Javob /tmp/javob.md ga yoziladi, workflow uni Issue'ga izoh qilib yuboradi."""
import os, re, json, sys
sys.path.insert(0, os.path.dirname(__file__))
import mijoz

title = (os.environ.get("ISSUE_TITLE") or "").strip()
body = (os.environ.get("ISSUE_BODY") or "").strip()
low = title.lower()
out = ""

if low.startswith("javob"):
    savol = re.sub(r"^javob\s*[:\-]?\s*", "", title, flags=re.I).strip()
    if not savol:
        out = "Mijoz savolini sarlavhaga yozing (tavsifga narx/muddat kabi ma'lumotlaringizni yozsangiz, javobga kiradi). Masalan: `javob: skameyka narxi qancha?`"
    else:
        txt, src = mijoz.javob_loyiha(savol, body)
        out = f"✍️ Javob loyihasi ({src}):\n\n{txt}\n\n— Nusxalab Direct'ga yuboring. Narx aniq bo'lsa o'zingiz qo'shing."
elif low.startswith("maqsad"):
    m = re.search(r"\d{3,6}", title.replace(" ", ""))
    if m:
        n = int(m.group())
        json.dump({"obunachi": n}, open("reja/maqsad.json", "w", encoding="utf-8"))
        out = f"🎯 Maqsad saqlandi: {n} obunachi. Keyingi tahlilda prognoz shu bo'yicha chiqadi."
    else:
        out = "Raqam yozing. Masalan: `maqsad 7000`"
elif low.startswith("raqobatchi"):
    names = [x.strip("@,. ").lower() for x in re.split(r"[\s,;]+", re.sub(r"^raqobatchi\s*[:\-]?\s*", "", title, flags=re.I)) if x.strip("@,. ")]
    names = [x for x in names if re.fullmatch(r"[a-z0-9._]{1,30}", x)][:5]
    if names:
        json.dump({"akkauntlar": names}, open("reja/raqobatchi.json", "w", encoding="utf-8"), ensure_ascii=False)
        out = "🕵️ Raqobatchilar saqlandi: " + ", ".join("@" + x for x in names) + \
              "\nEndi sarlavhasi `tahlil` bo'lgan Issue oching. Shaxsiy (business bo'lmagan) akkauntlar ochilmaydi."
    else:
        out = "Akkaunt nomlarini yozing. Masalan: `raqobatchi nom1 nom2` (5 tagacha, @ siz)"
else:
    out = "Buyruq tushunilmadi. Mavjudlari: `tahlil`, `javob: <mijoz savoli>`, `maqsad 7000`, `raqobatchi nom1 nom2`."
open("/tmp/javob.md", "w", encoding="utf-8").write(out)
print(out)
