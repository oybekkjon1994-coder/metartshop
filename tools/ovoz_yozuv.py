"""Sizning haqiqiy ovozingizni videoga montaj qiladi.

Qoida: ovoz fayli nomi = video fayli nomi.
  ovoz-yozuv/stellaj-buyurtma-1101.m4a  +  reels/stellaj-buyurtma-1101.mp4
  -> reels/stellaj-buyurtma-1101-ovoz.mp4  (videoning o'z ovozi past qilib saqlanadi)
Shu videoga ulangan, hali chiqmagan post reja/posts.json da avtomatik yangi (ovozli) faylga almashtiriladi.

  python tools/ovoz_yozuv.py [ovoz-yozuv/fayl.m4a ...]   (bo'sh bo'lsa: ovozli versiyasi yo'q hammasi)
"""
import os, sys, json, subprocess, glob, hashlib

EXT = (".m4a", ".mp3", ".wav", ".ogg", ".opus", ".aac", ".amr", ".3gp", ".mp4", ".webm", ".oga")


def run(args):
    subprocess.run(args, check=True)


def dur(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", p]).decode().strip())


def has_audio(p):
    return bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip())


VERSION = "2"  # ovoz qayta ishlash zanjiri o'zgarsa oshiriladi -> eski yozuvlar qayta montaj qilinadi

# tiniq ovoz: past shovqin kesiladi, shovqin kamaytiriladi, gap tiniqligi (2.5-4 kHz) ko'tariladi, siqish va balandlik tekislash
VOICE_CHAIN = ("highpass=f=90,lowpass=f=12000,afftdn=nr=14:nf=-28:tn=1,"
               "equalizer=f=220:t=q:w=1.0:g=-2.5,equalizer=f=3200:t=q:w=1.1:g=3.5,equalizer=f=7500:t=q:w=1.0:g=1.5,"
               "acompressor=threshold=0.09:ratio=3.2:attack=6:release=90:makeup=2.5,"
               "loudnorm=I=-13:TP=-1.2:LRA=7,alimiter=limit=0.93")


def mount(video, voice, out, orig_vol=0.55, delay=0.25):
    vd = dur(video)
    sr = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03"
    tmp = out + ".voice.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", voice, "-vn", "-af",
         f"{sr},areverse,{sr},areverse,{VOICE_CHAIN},aresample=44100,aformat=channel_layouts=stereo", tmp])
    vod = dur(tmp)
    total = max(vd, vod + delay + 0.4)
    ms = int(delay * 1000)
    fl = f"[1:a]adelay={ms}|{ms},asplit=2[v][vsc]"
    if has_audio(video):
        # videoning o'z tovushi gapirayotganda avtomatik pasayadi (sidechain), jim paytda tabiiy qoladi
        fl += (f";[0:a]aresample=44100,aformat=channel_layouts=stereo,volume={orig_vol}[o0];"
               f"[o0][vsc]sidechaincompress=threshold=0.015:ratio=12:attack=15:release=350:makeup=1[o]")
        mix, n = "[v][o]", 2
    else:
        fl += ";[vsc]anullsink" if False else ""
        mix, n = "[v]", 1
    fl += f";{mix}amix=inputs={n}:normalize=0:duration=longest,apad=whole_dur={total:.2f},atrim=0:{total:.2f}[aout]"
    vmap = "0:v"
    if total > vd + 0.05:
        fl = f"[0:v]tpad=stop_mode=clone:stop_duration={total - vd + 0.1:.2f}[vv];" + fl
        vmap = "[vv]"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", tmp, "-filter_complex", fl,
         "-map", vmap, "-map", "[aout]", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    os.remove(tmp)


def swap_posts(base):
    """Hali chiqmagan postlarda reels/<base>.mp4 ni ovozli versiyaga almashtiradi."""
    pp, hp = "reja/posts.json", "reja/holat.json"
    posts = json.load(open(pp, encoding="utf-8"))
    hol = json.load(open(hp, encoding="utf-8")) if os.path.exists(hp) else {}
    n = 0
    for p in posts:
        if hol.get(p["id"], {}).get("status") in ("chiqdi", "o'tkazildi"):
            continue
        for i, m in enumerate(p.get("media", [])):
            if m == f"repo:reels/{base}.mp4":
                p["media"][i] = f"repo:reels/{base}-ovoz.mp4"; n += 1
    if n:
        json.dump(posts, open(pp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return n


def next_unvoiced():
    """Hali chiqmagan, ovozsiz eng yaqin reel (reels/<nom>.mp4) nomini qaytaradi."""
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone(timedelta(hours=5)))
    hol = json.load(open("reja/holat.json", encoding="utf-8")) if os.path.exists("reja/holat.json") else {}
    cand = []
    for p in json.load(open("reja/posts.json", encoding="utf-8")):
        if p.get("type") != "REEL" or hol.get(p["id"], {}).get("status") in ("chiqdi", "o'tkazildi"):
            continue
        at = datetime.fromisoformat(p["at"])
        at = at if at.tzinfo else at.replace(tzinfo=timezone(timedelta(hours=5)))
        for m in p.get("media", []):
            if m.startswith("repo:reels/") and m.endswith(".mp4") and not m.endswith("-ovoz.mp4") and at >= now - timedelta(minutes=30):
                cand.append((at, m[len("repo:reels/"):-4]))
    return min(cand)[1] if cand else None


STATE = "ovoz-yozuv/.islangan.json"


def digest(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16] + ":" + VERSION


def main():
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    files = sys.argv[1:] or sorted(glob.glob("ovoz-yozuv/*"))
    done = 0
    for f in files:
        base, ext = os.path.splitext(os.path.basename(f))
        if ext.lower() not in EXT or base.endswith("-ovoz"):
            continue
        if not os.path.exists(f"reels/{base}.mp4") and not sys.argv[1:]:
            # nomi videoga mos emas: eng yaqin ovozsiz reelga biriktiramiz va faylni qayta nomlaymiz
            nb = next_unvoiced()
            if nb:
                nf = os.path.join(os.path.dirname(f), nb + ext.lower())
                os.rename(f, nf)
                print(f"{f}: eng yaqin ovozsiz reelga biriktirildi -> {nb}")
                f, base = nf, nb
        video, out = f"reels/{base}.mp4", f"reels/{base}-ovoz.mp4"
        if not os.path.exists(video):
            print(f"! {f}: mos video yo'q ({video}). Fayl nomi videoning nomi bilan bir xil bo'lsin."); continue
        if not sys.argv[1:] and os.path.exists(out) and state.get(base) == digest(f):
            continue
        print(f"Montaj: {video} + {f} -> {out}")
        mount(video, f, out)
        print(f"  almashtirilgan postlar: {swap_posts(base)}")
        state[base] = digest(f)
        json.dump(state, open(STATE, "w"), indent=1)
        done += 1
    print("Tayyor:", done)


if __name__ == "__main__":
    main()
