"""Haqiqiy ustaxona videolaridan Reels: (A) lazer uchqunlari, (B) do'kon jihozlash oldin->keyin + slayd-shou.
python3 tools/real_reels.py <manba_papka>   (manba: laser_slow.mp4, laser_perf.mp4, workshop.mp4, shop_empty.mp4, foto1..4.jpg)
Natija: reels/v2-*.mp4 (1080x1920, 30fps, lazerning o'z ovozi bilan) va ig/v2-karusel-*.jpg"""
import sys, os, math, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1]
BLACK = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
BOLD = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
YEL = (255, 194, 26)
_F = {}
def font(sz, b=BLACK):
    if (sz, b) not in _F: _F[(sz, b)] = ImageFont.truetype(b, sz)
    return _F[(sz, b)]
def ease(t): t = max(0, min(1, t)); return t * t * (3 - 2 * t)
def ctext(d, y, t, sz, fill='white', box=None, b=BLACK, stroke=0):
    f = font(sz, b); w = d.textlength(t, font=f); x = (W - w) / 2
    if box: d.rounded_rectangle((x - 28, y - 16, x + w + 28, y + sz * 1.08 + 16), 22, fill=box)
    d.text((x, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill='black')
def src(n): return os.path.join(SRC, n)

def frames(path, start, dur, speed=1.0):
    """Manba videodan 1080x1920 kadrlar (aylanish avtomatik), speed<1 — sekinlashtirish."""
    n = int(round(dur * FPS))
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts=PTS/{speed},fps={FPS}"
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(start), '-i', path, '-t', str(dur * speed + 0.5), '-vf', vf,
                          '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    last = None
    for _ in range(n):
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        last = Image.frombytes('RGB', (W, H), b); yield last
    p.stdout.close(); p.wait()

class Video:
    def __init__(self, name):
        self.tmp = os.path.join(SRC, name + '.v.mp4'); self.out = os.path.join(ROOT, 'reels', name + '.mp4'); self.n = 0
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                                   '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', self.tmp], stdin=subprocess.PIPE)
    def add(self, fr): self.p.stdin.write(fr.convert('RGB').tobytes()); self.n += 1
    def close(self, audio_src, a_start=0, vol=0.55):
        self.p.stdin.close(); self.p.wait(); dur = self.n / FPS
        # ovoz: lazerning haqiqiy shovqini (fon), oxirida so'nadi
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', self.tmp, '-ss', str(a_start), '-stream_loop', '-1', '-i', audio_src,
                        '-filter_complex', f'[1:a]volume={vol},afade=t=out:st={dur - 1.2:.2f}:d=1.2,atrim=0:{dur:.2f}[a]',
                        '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', self.out], check=True)
        os.remove(self.tmp); print(self.out, round(dur, 1), 's')

def overlay(fr, top=None, top2=None, label=None, small=None, k=0):
    d = ImageDraw.Draw(fr, 'RGBA')
    if top: ctext(d, 200, top, 78, fill='white', stroke=5)
    if top2: ctext(d, 310, top2, 84, fill='#111', box=YEL)
    if label:
        a = ease(k / 6); sz = int(64 + 8 * a)
        ctext(d, 1560, label, sz, fill='white', box=(0, 0, 0, 175))
    if small: ctext(d, 1680, small, 42, fill=YEL, box=(0, 0, 0, 150), b=BOLD)
    return fr

def flash(v, fr, n=4):
    for k in range(n): v.add(Image.blend(fr, Image.new('RGB', (W, H), 'white'), 0.7 * (1 - k / n)))

def endcard(v, dur, l1, l2, l3, l4=''):
    for k in range(int(dur * FPS)):
        fr = Image.new('RGB', (W, H), (14, 14, 18)); d = ImageDraw.Draw(fr)
        r = 240 + int(8 * math.sin(k / 5)); cx, cy = W // 2, 600
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=YEL)
        f = font(100); w = d.textlength('METART', font=f); d.text((cx - w / 2, cy - 92), 'METART', font=f, fill='#111')
        f = font(48, BOLD); w = d.textlength('S  H  O  P', font=f); d.text((cx - w / 2, cy + 28), 'S  H  O  P', font=f, fill='#111')
        ctext(d, 960, l1, 62); ctext(d, 1060, l2, 46, fill='#bbb', b=BOLD)
        ctext(d, 1190, l3, int(70 + 8 * ease(k / 15)), fill='#111', box=YEL)
        if l4: ctext(d, 1340, l4, 44, fill=YEL, b=BOLD)
        ctext(d, 1700, "Toshkent · O'zbekiston bo'ylab", 36, fill='#888', b=BOLD)
        v.add(fr)

# ---------- A) Lazer uchqunlari ----------
def reel_lazer():
    v = Video('v2-lazer-uchqun'); last = None
    seq = [  # fayl, boshlanish, davomiylik(chiqish), tezlik, matnlar
        ('laser_slow.mp4', 0.3, 3.6, 0.25, dict(top='LAZER METALLNI', top2="SARIYOG'DEK KESADI")),
        ('laser_perf.mp4', 1.0, 2.0, 1.5, dict(label='Teshikma-teshik, aniq')),
        ('laser_perf.mp4', 7.4, 2.4, 1.0, dict(label='Uchqunlar — bu bizning ish')),
        ('workshop.mp4', 0.0, 2.0, 1.0, dict(label='Bizning ustaxona')),
        ('laser_slow.mp4', 5.0, 3.0, 0.5, dict(label='Har qanday chizma', small="DXF yuboring — narxi darhol")),
        ('laser_perf.mp4', 17.0, 2.0, 1.0, dict(label='Darvoza · panjara · dekor')),
    ]
    for i, (f, s, dur, sp, txt) in enumerate(seq):
        for k, fr in enumerate(frames(src(f), s, dur, sp)):
            if i and k == 0: flash(v, fr, 3)
            last = overlay(fr, k=k, **txt); v.add(last)
    endcard(v, 2.6, 'Lazer kesish xizmati', 'Metall, zanglamas, alyuminiy', '@Metart_shop_bot', 'Telegram bot · 24/7')
    v.close(src('laser_perf.mp4'), a_start=0.5, vol=0.6)

# ---------- B) Do'kon jihozlash: oldin -> keyin ----------
def photo_pan(v, im, dur, label=None, small=None, direction=1, top=None, top2=None):
    """Gorizontal rasmni vertikal kadrda chapdan o'ngga suradi (Ken Burns)."""
    n = int(dur * FPS); k0 = H / im.height * 1.0
    big = im.resize((int(im.width * k0 * 1.08), int(im.height * k0 * 1.08)), Image.LANCZOS)
    span = big.width - W
    for k in range(n):
        t = ease(k / (n - 1)); x = int(span * (t if direction > 0 else 1 - t)); y = (big.height - H) // 2
        fr = big.crop((x, y, x + W, y + H))
        if k == 0: flash(v, fr, 3)
        v.add(overlay(fr, top=top, top2=top2, label=label, small=small, k=k))

def reel_dokon():
    v = Video('v2-dokon-oldin-keyin')
    for k, fr in enumerate(frames(src('shop_empty.mp4'), 0.0, 2.2, 2.0)):
        v.add(overlay(fr, top="BO'M-BO'SH DO'KON", top2='OLDIN', k=k))
    for k, fr in enumerate(frames(src('shop_empty.mp4'), 11.5, 2.0, 2.0)):
        if k == 0: flash(v, fr, 3)
        v.add(overlay(fr, label="Stellaj relslari o'rnatilmoqda", k=k))
    for k, fr in enumerate(frames(src('laser_perf.mp4'), 7.6, 1.5, 1.0)):
        if k == 0: flash(v, fr, 3)
        v.add(overlay(fr, label='Detallar — lazerda', k=k))
    photos = [ImageOps.exif_transpose(Image.open(src(f'foto{i}.jpg'))).convert('RGB') for i in (2, 3, 1, 4)]
    caps = [('KEYIN', 'Devor stellajlari + yoritish'), ('Oltin rangli ilgichlar', "Bolalar kiyimi uchun"), ('Yoritgichli oyna', "Do'kon dizayni bilan"), ("To'liq jihozlash", 'Bolalar kiyim do\'koni')]
    for i, (im, (lab, sm)) in enumerate(zip(photos, caps)):
        photo_pan(v, im, 2.3, label=lab, small=sm, direction=1 if i % 2 == 0 else -1)
    endcard(v, 2.8, "Do'koningizni jihozlaymiz", 'Stellaj · ilgich · peshtaxta · dekor', '@Metart_shop_bot', 'Telegram @lazekametal')
    v.close(src('laser_perf.mp4'), a_start=3.0, vol=0.35)

# ---------- C) Karusel (4:5) ----------
def karusel():
    os.makedirs(os.path.join(ROOT, 'ig'), exist_ok=True); CW, CH = 1080, 1350; outs = []
    photos = [ImageOps.exif_transpose(Image.open(src(f'foto{i}.jpg'))).convert('RGB') for i in (2, 3, 1, 4)]
    cover = ImageOps.fit(photos[0], (CW, CH), centering=(0.3, 0.5)); d = ImageDraw.Draw(cover, 'RGBA')
    d.rectangle((0, CH - 430, CW, CH), fill=(0, 0, 0, 170))
    for y, t, sz, col in [(CH - 390, "BOLALAR KIYIM DO'KONI", 64, 'white'), (CH - 300, "To'liq jihozladik", 54, YEL)]:
        f = font(sz); w = d.textlength(t, font=f); d.text(((CW - w) / 2, y), t, font=f, fill=col)
    f = font(40, BOLD)
    for i, t in enumerate(['Stellajlar · ilgichlar · yoritish', 'Buyurtma: @Metart_shop_bot']):
        w = d.textlength(t, font=f); d.text(((CW - w) / 2, CH - 200 + i * 62), t, font=f, fill='white')
    d.rounded_rectangle((40, 40, 330, 110), 20, fill=YEL); d.text((62, 52), 'METARTSHOP', font=font(40), fill='#111')
    outs.append(cover)
    for im, c in zip(photos[1:], [(0.5, 0.5), (0.35, 0.5), (0.6, 0.5)]): outs.append(ImageOps.fit(im, (CW, CH), centering=c))
    paths = []
    for i, o in enumerate(outs):
        p = os.path.join(ROOT, 'ig', f'v2-karusel-{i + 1}.jpg'); o.save(p, quality=90); paths.append(p)
    print(paths)

if __name__ == '__main__':
    which = sys.argv[2:] or ['lazer', 'dokon', 'karusel']
    if 'lazer' in which: reel_lazer()
    if 'dokon' in which: reel_dokon()
    if 'karusel' in which: karusel()
