"""Faqat lazer kesish kadrlaridan, qo'shiq zarbiga (beat) moslangan reels.
python3 tools/lazer_ritm.py <manba_papka> <qoshiq.m4a> <nom> <beat_s> <birinchi_beat_s>"""
import sys, os, subprocess
from PIL import Image, ImageOps
SRC_DIR, SONG, NAME, BEAT, FIRST = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4]), float(sys.argv[5])
sys.argv = [sys.argv[0], SRC_DIR]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import noyabr_reels as R

CLIPS = {  # klip: qiziq joylar (soniya)
    'uchqun_hd.mp4': [1, 3, 5, 7, 9, 11, 13],
    'kesish3_hd.mp4': [2, 5, 9, 12, 15],
    'kesish1_hd.mp4': [1, 4, 7, 10],
    'kesish2_hd.mp4': [1, 4, 7],
    'mers_kesish_hd.mp4': [2, 6, 10, 14, 18],
}
ORDER = ['uchqun_hd.mp4', 'kesish3_hd.mp4', 'mers_kesish_hd.mp4', 'kesish1_hd.mp4', 'uchqun_hd.mp4', 'kesish2_hd.mp4']

def punch(fr, k, n):
    """Zarbda kichik 'zoom' turtki."""
    z = 1.0 + 0.06 * max(0, 1 - k / 6)
    if z <= 1.001: return fr
    w, h = fr.size; cw, ch = int(w / z), int(h / z)
    return fr.crop(((w - cw) // 2, (h - ch) // 2, (w + cw) // 2, (h + ch) // 2)).resize((w, h), Image.BILINEAR)

def main():
    total = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', SONG],
                                 capture_output=True, text=True).stdout) - 0.8
    v = R.Video(NAME)
    cuts = [0.0] + [FIRST + i * BEAT for i in range(2, 200) if FIRST + i * BEAT < total - 1.8]
    end_at = total - 1.8
    used = {c: 0 for c in CLIPS}; seg = 0
    for i, t0 in enumerate(cuts):
        t1 = cuts[i + 1] if i + 1 < len(cuts) else end_at
        d = t1 - t0
        clip = ORDER[seg % len(ORDER)]; seg += 1
        st = CLIPS[clip][used[clip] % len(CLIPS[clip])]; used[clip] += 1
        slow = (i % 4 == 3)  # har 4-kadr sekinlashtirilgan — uchqunlar ko'rinsin
        for k, fr in enumerate(R.frames(R.src(clip), st, d, 0.5 if slow else 1.0)):
            fr = punch(fr, k, d)
            if i == 0: R.overlay(fr, top='Ovozni yoqing', top2='Lazer + ritm')
            if k < 2 and i: fr = Image.blend(fr, Image.new('RGB', fr.size, 'white'), 0.3 if k == 0 else 0.1)
            v.add(fr)
        while v.t < t1 - 1e-3: v.add(fr)
    R.endcard(v, total - v.t, 'DXF yuboring —', 'narxini darhol hisoblaymiz', R.BOT, 'Telegram: @lazekametal')
    v.p.stdin.close(); v.p.wait()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', v.tmp, '-i', SONG, '-map', '0:v', '-map', '1:a',
                    '-af', f'afade=t=out:st={total - 1.0:.2f}:d=1.0', '-t', f'{total:.2f}', '-c:v', 'copy', '-c:a', 'aac',
                    '-b:a', '192k', '-movflags', '+faststart', v.out], check=True)
    os.remove(v.tmp); print(v.out, round(v.t, 1), 'kesimlar:', len(cuts))

main()
