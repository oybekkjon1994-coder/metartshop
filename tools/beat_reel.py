"""Namuna videoning ritmi va qo'shig'i bo'yicha mahsulotlarimizdan reels.
python3 tools/beat_reel.py <manba_papka> <qoshiq.m4a> <nom>"""
import sys, os, subprocess
from PIL import Image, ImageOps, ImageDraw
SRC_DIR, SONG, NAME = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = [sys.argv[0], SRC_DIR]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noyabr_reels as R

# (boshlanish, manba, manba_start, effekt, matn) — kesish nuqtalari namuna videodagi sahna almashinuvlaridan
PLAN = [
    (0.00, 'kesish3.mp4', 4.0, 'slow', ('Hammasi', 'lazerdan boshlanadi')),
    (3.60, 'kesish1.mp4', 2.0, 'slow', None),
    (7.17, 'mers_kesish.mp4', 5.0, '', None),
    (8.67, 'barca_ai.mp4', 1.0, 'fit', ('', 'Barselona · chiroqli')),
    (12.0, 'arsenal.jpg', 0, 'bw', None),
    (12.8, 'liverpool.jpg', 0, 'bw', None),
    (13.57, 'kesish2.mp4', 3.0, 'bw', None),
    (14.53, 'real.jpg', 0, 'bw', None),
    (15.93, 'mers_ai.mp4', 4.0, 'fit', ('', 'Mashinangiz — devorda')),
    (18.80, 'city_chiroq.jpg', 0, '', None),
    (20.27, 'barca.jpg', 0, '', None),
    (21.67, 'city.jpg', 0, '', None),
    (22.53, 'real_ai.mp4', 2.0, 'fit', ('', "Eng zo'r sovg'a")),
    (24.60, 'kesish3.mp4', 10.0, '', None),
    (27.33, 'urna2.jpg', 0, '', ('', 'Saralash urnasi')),
    (29.40, 'mers_ai.mp4', 7.0, 'fit', None),
    (31.27, 'kesish1.mp4', 8.0, '', None),
    (32.47, 'arsenal.jpg', 0, 'bw', None),
    (33.27, 'liverpool.jpg', 0, 'bw', None),
    (34.00, 'END', 0, '', None),
]

def main():
    total = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', SONG],
                                 capture_output=True, text=True).stdout)
    v = R.Video(NAME)
    for i, (t0, src, st, fx, txt) in enumerate(PLAN):
        t1 = PLAN[i + 1][0] if i + 1 < len(PLAN) else total
        d = t1 - t0
        if src == 'END':
            R.endcard(v, d, 'Metall + lazer = san\'at', 'soat · dekor · chiroq · urna', R.BOT, 'Telegram: @lazekametal'); continue
        if src.endswith('.jpg'):
            gen = R.photo(R.src(src), d, (1.0, 1.15))
        else:
            gen = R.frames(R.src(src), st, d, 0.6 if fx == 'slow' else 1.0, fit=(fx == 'fit'))
        for k, fr in enumerate(gen):
            if fx == 'bw': fr = ImageOps.grayscale(fr).convert('RGB')
            if txt: R.overlay(fr, top=txt[0] or None, top2=txt[1], k=k)
            if k < 2 and i: fr = Image.blend(fr, Image.new('RGB', fr.size, 'white'), 0.35 if k == 0 else 0.15)
            v.add(fr)
        while v.t < t1 - 1e-3: v.add(fr)  # qisqa manba bo'lsa oxirgi kadrni ushlab turish
    v.p.stdin.close(); v.p.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v.tmp, '-i', SONG, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '192k', '-shortest', '-movflags', '+faststart', v.out], check=True)
    os.remove(v.tmp); print(v.out, round(v.t, 1))

main()
