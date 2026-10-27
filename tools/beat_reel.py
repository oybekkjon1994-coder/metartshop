"""Namuna videoning ritmi va qo'shig'i bo'yicha mahsulotlarimizdan reels.
python3 tools/beat_reel.py <manba_papka> <qoshiq.m4a> <nom>"""
import sys, os, subprocess
from PIL import Image, ImageOps, ImageDraw
SRC_DIR, SONG, NAME = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = [sys.argv[0], SRC_DIR]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noyabr_reels as R

# (boshlanish, manba, manba_start, effekt, matn) — kesish nuqtalari namuna videodagi sahna almashinuvlaridan
OFF = 9.0     # qo'shiq shu soniyadan boshlanadi (25 soniyalik montaj)
LENGTH = 25.0
PLAN = [
    (0.00, 'kesish3.mp4', 4.0, 'slow', ('Hammasi', 'lazerdan boshlanadi')),
    (3.00, 'arsenal.jpg', 0, 'bw', None),
    (3.80, 'liverpool.jpg', 0, 'bw', None),
    (4.57, 'kesish2.mp4', 3.0, 'bw', None),
    (5.53, 'barca.jpg', 0, 'bw', None),
    (6.93, 'mers_ai.mp4', 4.0, 'fit', ('', 'Mashinangiz — devorda')),
    (9.80, 'city_chiroq.jpg', 0, '', None),
    (11.27, 'barca.jpg', 0, '', None),
    (12.67, 'city.jpg', 0, '', None),
    (13.53, 'real.jpg', 0, '', ('', "Eng zo'r sovg'a")),
    (15.60, 'kesish3.mp4', 10.0, '', None),
    (18.33, 'barca_ai.mp4', 6.0, 'fit', ('', 'Chiroqli soatlar')),
    (20.40, 'mers_ai.mp4', 7.0, 'fit', None),
    (22.27, 'kesish1.mp4', 8.0, '', None),
    (23.47, 'END', 0, '', None),
]

def main():
    total = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', SONG],
                                 capture_output=True, text=True).stdout)
    total = min(total - OFF, LENGTH)
    v = R.Video(NAME)
    for i, (t0, src, st, fx, txt) in enumerate(PLAN):
        t1 = PLAN[i + 1][0] if i + 1 < len(PLAN) else total
        d = t1 - t0
        if src == 'END':
            R.endcard(v, d, 'Metall + lazer = san\'at', 'soat · dekor · chiroq', R.BOT, 'Telegram: @lazekametal'); continue
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
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v.tmp, '-ss', str(OFF), '-i', SONG, '-map', '0:v', '-map', '1:a', '-af', f'afade=t=out:st={total - 1.2:.2f}:d=1.2', '-t', f'{total:.2f}', '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '192k', '-shortest', '-movflags', '+faststart', v.out], check=True)
    os.remove(v.tmp); print(v.out, round(v.t, 1))

main()
