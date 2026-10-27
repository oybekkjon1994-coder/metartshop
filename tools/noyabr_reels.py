"""Noyabr 1-hafta Reels: haqiqiy lazer videolari, AI videolar va mahsulot rasmlaridan.
python3 tools/noyabr_reels.py <manba_papka> [nom ...]
Natija: reels/v7-*.mp4 (1080x1920, 30fps, o'zimizning fon musiqasi + asl ovoz past)."""
import sys, os, math, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = sys.argv[1]
BLACK = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
BOLD = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
YEL = (255, 194, 26)
BOT = '@Metart_shop_bot'
_F = {}
def font(sz, b=BLACK):
    if (sz, b) not in _F: _F[(sz, b)] = ImageFont.truetype(b, sz)
    return _F[(sz, b)]
def ease(t): t = max(0, min(1, t)); return t * t * (3 - 2 * t)
def ctext(d, y, t, sz, fill='white', box=None, b=BLACK, stroke=0):
    t = ''.join(c for c in t if ord(c) < 0x2000 or c in '·—').strip()  # emoji shriftda yo'q
    f = font(sz, b); w = d.textlength(t, font=f); x = (W - w) / 2
    if box: d.rounded_rectangle((x - 28, y - 16, x + w + 28, y + sz * 1.08 + 16), 22, fill=box)
    d.text((x, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill='black')
def src(n): return os.path.join(SRC, n)

def frames(path, start, dur, speed=1.0, fit=False):
    """1080x1920 kadrlar. fit=True: yotiq videoni to'liq ko'rsatadi, orqa fon xiralashtirilgan."""
    n = int(round(dur * FPS))
    if fit:
        vf = (f"setpts=PTS/{speed},fps={FPS},split[a][b];[a]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},"
              f"boxblur=30:3,eq=brightness=-0.12[bg];[b]scale={W}:-2[fg];[bg][fg]overlay=0:(H-h)/2")
    else:
        vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setpts=PTS/{speed},fps={FPS}"
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(start), '-i', path, '-t', str(dur * speed + 0.5), '-filter_complex', vf,
                          '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    last = None
    for _ in range(n):
        b = p.stdout.read(W * H * 3)
        if len(b) < W * H * 3: break
        last = Image.frombytes('RGB', (W, H), b); yield last
    p.stdout.close(); p.wait()
    k = 0
    while last is not None and k < n and False: yield last

def photo(path, dur, zoom=(1.0, 1.12)):
    """Rasmdan Ken Burns (sekin yaqinlashish) kadrlar, xira fon bilan."""
    im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
    bg = ImageOps.fit(im, (W, H)).filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * 0.6))
    s = min(W / im.width, H * 0.82 / im.height); base = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    n = int(dur * FPS)
    for k in range(n):
        z = zoom[0] + (zoom[1] - zoom[0]) * ease(k / max(1, n - 1))
        fg = base.resize((int(base.width * z), int(base.height * z)), Image.BILINEAR)
        fr = bg.copy(); fr.paste(fg, ((W - fg.width) // 2, (H - fg.height) // 2 + 40)); yield fr

class Video:
    def __init__(self, name):
        self.name = name; self.tmp = os.path.join(tempfile.gettempdir(), name + '.v.mp4')
        self.out = os.path.join(ROOT, 'reels', name + '.mp4'); self.n = 0; self.audio = []  # (manba, boshlanish_s_videoda, manba_start, dur, vol)
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                                   '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', self.tmp], stdin=subprocess.PIPE)
    @property
    def t(self): return self.n / FPS
    def add(self, fr): self.p.stdin.write(fr.convert('RGB').tobytes()); self.n += 1
    def sound(self, path, start, dur, vol=0.35, speed=1.0):
        self.audio.append((path, self.t, start, dur, vol, speed))
    def close(self, bpm=104, music_db=-12):
        self.p.stdin.close(); self.p.wait(); dur = self.t
        mus = os.path.join(tempfile.gettempdir(), self.name + '.wav')
        subprocess.run(['python3', os.path.join(ROOT, 'tools', 'minus.py'), f'{dur:.2f}', mus, str(bpm)], check=True, capture_output=True)
        ins = ['-i', self.tmp, '-i', mus]; flt = [f'[1:a]volume={music_db}dB[m]']; mix = ['[m]']
        for i, (p, at, st, d, vol, sp) in enumerate(self.audio):
            ins += ['-ss', str(st), '-t', str(d * sp), '-i', p]
            tempo = f'atempo={max(0.5, sp)},' if sp != 1 else ''
            flt.append(f'[{i + 2}:a]{tempo}volume={vol},afade=t=in:d=0.3,afade=t=out:st={max(0, d - 0.4):.2f}:d=0.4,adelay={int(at * 1000)}|{int(at * 1000)}[s{i}]')
            mix.append(f'[s{i}]')
        flt.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0,afade=t=out:st={dur - 1.2:.2f}:d=1.2,atrim=0:{dur:.2f}[a]")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(flt), '-map', '0:v', '-map', '[a]',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', self.out], check=True)
        os.remove(self.tmp); os.remove(mus); print(self.out, round(dur, 1), 's')

def overlay(fr, top=None, top2=None, label=None, small=None, k=0):
    d = ImageDraw.Draw(fr, 'RGBA')
    if top: ctext(d, 200, top, 76, fill='white', stroke=5)
    if top2: ctext(d, 310, top2, 80, fill='#111', box=YEL)
    if label:
        a = ease(k / 6); sz = int(60 + 8 * a)
        ctext(d, 1540, label, sz, fill='white', box=(0, 0, 0, 175))
    if small: ctext(d, 1670, small, 42, fill=YEL, box=(0, 0, 0, 150), b=BOLD)
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
        ctext(d, 1190, l3, int(66 + 8 * ease(k / 15)), fill='#111', box=YEL)
        if l4: ctext(d, 1340, l4, 44, fill=YEL, b=BOLD)
        ctext(d, 1700, "Toshkent · O'zbekiston bo'ylab", 36, fill='#888', b=BOLD)
        v.add(fr)

def clip(v, path, start, dur, speed=1.0, fit=False, vol=0.35, **ov):
    v.sound(src(path), start, dur, vol, speed)
    for k, fr in enumerate(frames(src(path), start, dur, speed, fit)):
        v.add(overlay(fr, k=k, **ov))

# ---------- 1) Lazer kesish jarayoni ----------
def reel_kesish():
    v = Video('v7-lazer-kesish')
    clip(v, 'kesish3.mp4', 5, 3.2, top='Lazer metallni', top2='qanday kesadi? 🔥', vol=0.6)
    clip(v, 'kesish1.mp4', 3, 3.0, label='Har qanday chizma', vol=0.6)
    clip(v, 'kesish2.mp4', 2, 3.0, speed=0.6, label='Aniqlik — millimetrgacha', vol=0.6)
    clip(v, 'kesish3.mp4', 10, 3.5, label='Uchqunlar 😍', vol=0.6)
    clip(v, 'kesish1.mp4', 8, 3.0, label='Yaxshi qism — oxirida 👇', vol=0.6)
    endcard(v, 3.2, 'DXF yuboring —', 'narxini darhol hisoblaymiz', BOT, 'Telegram: @lazekametal')
    v.close(bpm=112)

# ---------- 2) Mersedes: kesishdan chiroqqacha ----------
def reel_mers():
    v = Video('v7-mersedes-chiroq')
    clip(v, 'mers_ai.mp4', 0, 3.0, fit=True, top='Mashinangiz', top2='devoringizda ✨', vol=0.25)
    clip(v, 'mers_kesish.mp4', 4, 3.5, label='Lazer bilan kesamiz', vol=0.6)
    clip(v, 'mers_kesish.mp4', 14, 3.0, speed=0.7, label='Metall, 1 donadan', vol=0.6)
    clip(v, 'mers_ai.mp4', 3.0, 7.0, fit=True, label='Chiroqli devor dekori', small="Istalgan mashina modeli", vol=0.25)
    endcard(v, 3.2, 'Mashina rasmini yuboring —', 'chizib, kesib beramiz', BOT, 'Telegram: @lazekametal')
    v.close(bpm=118)

# ---------- 3) Barselona soati ----------
def reel_barca():
    v = Video('v7-barca-chiroq')
    clip(v, 'barca_ai.mp4', 0, 10.0, fit=True, top='Barselona muxlisi?', top2='Bu soat siz uchun 💙❤️', vol=0.3)
    for k, fr in enumerate(photo(src('barca.jpg'), 3.0)):
        v.add(overlay(fr, label='Haqiqiy mahsulot', small='Metall · lazer bilan kesilgan', k=k))
    endcard(v, 3.0, 'Istalgan klub logotipi', 'chiroqli yoki oddiy', BOT, 'Telegram: @lazekametal')
    v.close(bpm=108)

# ---------- 4) Real Madrid soati ----------
def reel_real():
    v = Video('v7-real-sovga')
    clip(v, 'real_ai.mp4', 0, 10.0, fit=True, top="Do'stingizga sovg'a", top2='izlayapsizmi? 🎁', vol=0.3)
    for k, fr in enumerate(photo(src('real.jpg'), 3.0)):
        v.add(overlay(fr, label='Real Madrid soati', small='Metall · lazer bilan kesilgan', k=k))
    endcard(v, 3.0, "Ajoyib sovg'a —", 'istalgan klub logotipi bilan', BOT, 'Telegram: @lazekametal')
    v.close(bpm=100)

# ---------- 5) Klublar: qaysi biri seniki? ----------
def reel_klublar():
    v = Video('v7-klublar-tanla')
    items = [('arsenal.jpg', '1 · Arsenal'), ('liverpool.jpg', '2 · Liverpool'), ('barca.jpg', '3 · Barselona'),
             ('real.jpg', '4 · Real Madrid'), ('city.jpg', '5 · Manchester City'), ('city_chiroq.jpg', '6 · City — chiroqli ✨')]
    for i, (p, lab) in enumerate(items):
        fr0 = None
        for k, fr in enumerate(photo(src(p), 2.0, (1.04, 1.12))):
            if fr0 is None: fr0 = fr
            v.add(overlay(fr, top='Qaysi biri SENIKI?' if i < 2 else None, top2='Raqamini yoz 👇' if i < 2 else None, label=lab, k=k))
    endcard(v, 3.0, 'Izohga raqamini yoz!', "Do'stingni belgila 😄", BOT, 'Istalgan klub — buyurtma bilan')
    v.close(bpm=120)

# ---------- 6) Saralash qutisi (urna) ----------
def reel_urna():
    v = Video('v7-saralash-urna')
    for k, fr in enumerate(photo(src('urna2.jpg'), 3.5)):
        v.add(overlay(fr, top='Chiqindini saralash', top2='uchun metall urna ♻️', k=k))
    for k, fr in enumerate(photo(src('urna1.jpg'), 3.5)):
        v.add(overlay(fr, label="3 bo'lim: plastik, qog'oz", small='Maktab · park · ofis · savdo markazi', k=k))
    for k, fr in enumerate(photo(src('urna2.jpg'), 2.5, (1.12, 1.25))):
        v.add(overlay(fr, label="Rang — buyurtma bo'yicha", k=k))
    endcard(v, 3.2, 'Tashkilotlar uchun', 'ulgurji buyurtma qabul qilamiz', 'Telegram: @lazekametal', BOT)
    v.close(bpm=96)

ALL = {'kesish': reel_kesish, 'mers': reel_mers, 'barca': reel_barca, 'real': reel_real, 'klublar': reel_klublar, 'urna': reel_urna}
if __name__ == '__main__':
    for n in (sys.argv[2:] or ALL): ALL[n]()
