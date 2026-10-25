"""Metartshop "portlaydigan" Reels: 3 ta dinamik video (1080x1920, 30fps, ovozsiz — ovoz tools/ovoz orqali).
python3 tools/viral_reels.py <ishchi_papka>  (ishchi papkada: mylogo.png, logo.dxf, prev_qora/oltin/oq/qizil.jpg)
"""
import sys, os, math, random, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

W, H, FPS = 1080, 1920, 30
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WD = sys.argv[1]
BLACK = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'
BOLD = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
YEL = (255, 194, 26)
F = {}
def font(sz, b=BLACK):
    k = (sz, b)
    if k not in F: F[k] = ImageFont.truetype(b, sz)
    return F[k]
def img(p): return ImageOps.exif_transpose(Image.open(p)).convert('RGB')
def ease(t): t = max(0, min(1, t)); return t * t * (3 - 2 * t)

def ctext(d, y, t, sz, fill='white', box=None, b=BLACK, pad=(28, 16), stroke=0):
    f = font(sz, b); w = d.textlength(t, font=f); x = (W - w) / 2
    if box: d.rounded_rectangle((x - pad[0], y - pad[1], x + w + pad[0], y + sz * 1.08 + pad[1]), 22, fill=box)
    d.text((x, y), t, font=f, fill=fill, stroke_width=stroke, stroke_fill='black')
    return w

def fit(im, maxw, maxh, s=1.0):
    k = min(maxw / im.width, maxh / im.height) * s
    return im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)

def blurbg(im, dark=0.45):
    return ImageOps.fit(im, (W, H)).filter(ImageFilter.GaussianBlur(40)).point(lambda v: int(v * dark))

class Video:
    def __init__(self, name):
        self.path = os.path.join(ROOT, 'reels', name)
        self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                                   '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', self.path], stdin=subprocess.PIPE)
        self.n = 0
    def add(self, fr): self.p.stdin.write(fr.convert('RGB').tobytes()); self.n += 1
    def close(self): self.p.stdin.close(); self.p.wait(); print(self.path, round(self.n / FPS, 1), 's')

def endcard(v, dur, l1, l2, small=''):
    n = int(dur * FPS)
    for k in range(n):
        fr = Image.new('RGB', (W, H), (14, 14, 18)); d = ImageDraw.Draw(fr)
        r = 250 + int(8 * math.sin(k / 5)); cx, cy = W // 2, 640
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=YEL)
        f = font(104); w = d.textlength('METART', font=f); d.text((cx - w / 2, cy - 95), 'METART', font=f, fill='#111')
        f = font(50, BOLD); w = d.textlength('S  H  O  P', font=f); d.text((cx - w / 2, cy + 30), 'S  H  O  P', font=f, fill='#111')
        ctext(d, 1010, l1, 58)
        a = ease(k / (FPS * 0.5)); sz = int(70 + 10 * a)
        ctext(d, 1130, l2, sz, fill='#111', box=YEL)
        ctext(d, 1290, 'Telegram bot  ·  24/7', 44, fill='#bbb', b=BOLD)
        if small: ctext(d, 1400, small, 44, fill=YEL, b=BOLD)
        ctext(d, 1700, "Toshkent va butun O'zbekiston bo'ylab yetkazamiz", 34, fill='#888', b=BOLD)
        v.add(fr)

# ---------- 1) Logotipdan soatgacha ----------
def parse_dxf(p):
    lines = open(p, encoding='latin1').read().split('\n'); pairs = [(lines[i].strip(), lines[i + 1].strip()) for i in range(0, len(lines) - 1, 2)]
    paths, cur, ent = [], None, None; cx = cy = None
    for c, v in pairs:
        if c == '0':
            if ent == 'CIRCLE' and cx is not None:
                paths.append([(cx + rr * math.cos(a / 40 * 2 * math.pi), cy + rr * math.sin(a / 40 * 2 * math.pi)) for a in range(41)])
            ent = v; cx = cy = None
            if v == 'POLYLINE': cur = []; paths.append(cur)
            elif v == 'SEQEND': cur = None
            continue
        if ent == 'VERTEX' and cur is not None:
            if c == '10': cur.append([float(v), 0])
            elif c == '20': cur[-1][1] = float(v)
        if ent == 'CIRCLE':
            if c == '10': cx = float(v)
            elif c == '20': cy = float(v)
            elif c == '40': rr = float(v)
    paths = [[tuple(q) for q in pth] for pth in paths if len(pth) > 1]
    for pth in paths:
        if pth[0] != pth[-1]: pth.append(pth[0])
    return paths

def reel_logo():
    v = Video('v1-logo-soat.mp4')
    logo = img(os.path.join(WD, 'mylogo.png'))
    # 0-1.8: logotip + ilgak
    for k in range(int(1.8 * FPS)):
        fr = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(fr)
        s = 1 + 0.04 * k / FPS; L = fit(logo, 760, 760, s); fr.paste(L, ((W - L.width) // 2, 640 - (L.height - 760) // 2))
        ctext(d, 230, 'LOGOTIPINGIZ', 92, fill='#111')
        ctext(d, 350, 'METALL SOATGA', 92, fill='#111', box=YEL)
        ctext(d, 1520, 'aylanadi... 10 soniyada', 56, fill='#444', b=BOLD)
        v.add(fr)
    # 1.8-6: lazer chizmoqda
    paths = parse_dxf(os.path.join(WD, 'logo.dxf'))
    xs = [x for p in paths for x, _ in p]; ys = [y for p in paths for _, y in p]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys); sc = 820 / max(x1 - x0, y1 - y0)
    T = lambda x, y: (W / 2 + (x - (x0 + x1) / 2) * sc, 1010 - (y - (y0 + y1) / 2) * sc)
    segs = []
    for p in paths:
        for a, b in zip(p, p[1:]): segs.append((T(*a), T(*b), math.dist(a, b)))
    total = sum(s[2] for s in segs); n = int(4.2 * FPS); rnd = random.Random(3); sparks = []
    base = Image.new('RGB', (W, H), (12, 12, 16)); gd = ImageDraw.Draw(base)
    for gx in range(0, W, 60): gd.line((gx, 0, gx, H), fill=(22, 22, 28))
    for gy in range(0, H, 60): gd.line((0, gy, W, gy), fill=(22, 22, 28))
    for k in range(n):
        lim = total * ease((k + 1) / n) ; acc = 0
        lay = Image.new('RGB', (W, H), (0, 0, 0)); ld = ImageDraw.Draw(lay); head = None
        for a, b, L in segs:
            if acc >= lim: break
            t = min(1, (lim - acc) / L) if L else 1
            e = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            ld.line((a, e), fill=(255, 150, 20), width=7); head = e; acc += L
        glow = lay.filter(ImageFilter.GaussianBlur(10))
        fr = Image.composite(Image.new('RGB', (W, H), (255, 170, 40)), base, glow.convert('L').point(lambda q: min(255, q * 2)))
        fr = Image.composite(Image.new('RGB', (W, H), (255, 236, 200)), fr, lay.convert('L').point(lambda q: 255 if q > 40 else 0))
        d = ImageDraw.Draw(fr, 'RGBA')
        if head:
            for _ in range(7): sparks.append([head[0], head[1], rnd.uniform(-9, 9), rnd.uniform(-14, 2), rnd.randint(8, 18)])
            d.ellipse((head[0] - 16, head[1] - 16, head[0] + 16, head[1] + 16), fill=(255, 255, 255, 255))
            d.ellipse((head[0] - 34, head[1] - 34, head[0] + 34, head[1] + 34), fill=(255, 200, 80, 70))
        for sp in sparks:
            sp[0] += sp[2]; sp[1] += sp[3]; sp[3] += 1.2; sp[4] -= 1
            if sp[4] > 0: d.line((sp[0], sp[1], sp[0] - sp[2] * 1.6, sp[1] - sp[3] * 1.6), fill=(255, 200 + rnd.randint(0, 55), 80, 230), width=3)
        sparks = [s for s in sparks if s[4] > 0]
        ctext(d, 230, 'LAZER KESMOQDA', 84, fill='#111', box=YEL)
        ctext(d, 1590, f'{int(100 * ease((k + 1) / n))}%', 64, fill='white')
        v.add(fr)
    # chaqnash
    prev = {c: img(os.path.join(WD, f'prev_{c}.jpg')) for c in ['qora', 'oltin', 'oq', 'qizil']}
    for k in range(6):
        v.add(Image.blend(Image.new('RGB', (W, H), 'white'), ImageOps.fit(prev['qora'], (W, H)), k / 6))
    names = [('qora', 'QORA'), ('oltin', 'OLTIN'), ('oq', 'OQ'), ('qizil', 'QIZIL')]
    for i, (c, lab) in enumerate(names):
        P = prev[c]
        for k in range(int(1.05 * FPS)):
            bg = blurbg(P, 0.6); s = 1.0 + 0.05 * k / FPS + (0.06 * (1 - ease(k / 6)) if i else 0)
            pp = fit(P, 1000, 1000, s); bg.paste(pp, ((W - pp.width) // 2, 460 - (pp.height - 1000) // 2))
            d = ImageDraw.Draw(bg, 'RGBA')
            ctext(d, 200, 'ISTALGAN RANG', 84, fill='#111', box=YEL)
            ctext(d, 1560, lab, 96, fill='white', box=(0, 0, 0, 170))
            v.add(bg)
    endcard(v, 2.6, 'Logotipingizni yuboring:', '@Metart_shop_bot', "40 sm — 150 000 so'm")
    v.close()

# ---------- 2) Qaysi klub sizniki? ----------
CLUBS = [('barselona-soat', 'BARSELONA'), ('real-madrid-soat', 'REAL MADRID'), ('man-city-soat', 'MAN CITY'), ('chelsea-soat', 'CHELSEA'),
         ('arsenal-soat', 'ARSENAL'), ('liverpool-soat', 'LIVERPOOL'), ('man-united-soat', 'MAN UNITED'), ('nasaf-soat', 'FC NASAF')]
def reel_klub():
    v = Video('v1-qaysi-klub.mp4')
    ims = [img(os.path.join(ROOT, 'img', f'{c}-1.jpg')) for c, _ in CLUBS]
    # ilgak: kollaj
    col = Image.new('RGB', (W, H))
    for i, im in enumerate(ims): t = ImageOps.fit(im, (W // 2, H // 4)); col.paste(t, ((i % 2) * W // 2, (i // 2) * H // 4))
    col = col.point(lambda q: int(q * 0.45))
    for k in range(int(1.7 * FPS)):
        fr = col.copy(); d = ImageDraw.Draw(fr, 'RGBA')
        s = int(118 + 14 * ease(k / 8))
        ctext(d, 640, 'QAYSI BIRI', s, fill='white', stroke=4)
        ctext(d, 800, 'SENIKI?', s + 20, fill='#111', box=YEL)
        ctext(d, 1060, 'Raqamini izohga yoz', 60, fill='white', box=(0, 0, 0, 170), b=BOLD)
        v.add(fr)
    for i, (im, (_, nm)) in enumerate(zip(ims, CLUBS)):
        bg = blurbg(im, 0.5)
        for k in range(int(1.0 * FPS)):
            fr = bg.copy(); s = 1.12 - 0.12 * ease(k / 7) + 0.03 * k / FPS
            pp = fit(im, 1000, 1180, s); fr.paste(pp, ((W - pp.width) // 2, 400 - (pp.height - 1180) // 2))
            d = ImageDraw.Draw(fr, 'RGBA')
            r = 120; d.ellipse((W // 2 - r, 140, W // 2 + r, 140 + 2 * r), fill=YEL)
            f = font(150); t = str(i + 1); w = d.textlength(t, font=f); d.text((W / 2 - w / 2, 165), t, font=f, fill='#111')
            ctext(d, 1640, nm, 88, fill='white', box=(0, 0, 0, 180))
            if k < 3: d.rectangle((0, 0, W, H), fill=(255, 255, 255, 120 - 40 * k))
            v.add(fr)
    # yakun: 2x4 panjara
    for k in range(int(2.4 * FPS)):
        fr = Image.new('RGB', (W, H), (14, 14, 18)); d = ImageDraw.Draw(fr, 'RGBA')
        cw, ch = 500, 330
        for i, im in enumerate(ims):
            t = ImageOps.fit(im, (cw, ch)); x = 27 + (i % 2) * (cw + 26); y = 330 + (i // 2) * (ch + 26)
            fr.paste(t, (x, y)); d.ellipse((x + 14, y + 14, x + 94, y + 94), fill=YEL)
            f = font(58); s = str(i + 1); w = d.textlength(s, font=f); d.text((x + 54 - w / 2, y + 20), s, font=f, fill='#111')
        ctext(d, 150, 'IZOHGA YOZ: 1–8 ?', 80, fill='#111', box=YEL)
        ctext(d, 1810, "Buyurtma: @Metart_shop_bot", 50, fill='white', b=BOLD)
        v.add(fr)
    endcard(v, 1.8, "Istalgan klub logotipi bilan:", '@Metart_shop_bot', "150 000 so'mdan")
    v.close()

# ---------- 3) Oq bo'rilar ----------
def reel_borilar():
    v = Video('v1-oq-borilar.mp4')
    im = img(os.path.join(ROOT, 'img', 'oq-borilar-2026-1.jpg')); im = im.crop((0, 0, im.width, int(im.height * 0.86))); gerb = img(os.path.join(ROOT, 'img', 'gerb-soat-1.jpg'))
    flag = [(30, 144, 210), (255, 255, 255), (30, 160, 70)]
    def stripes(fr, k):
        d = ImageDraw.Draw(fr)
        for i, c in enumerate(flag):
            w = int(W * ease((k - i * 3) / 12)); d.rectangle((0, 40 + i * 26, w, 40 + i * 26 + 20), fill=c)
            d.rectangle((W - w, H - 120 + i * 26, W, H - 100 + i * 26), fill=c)
    for k in range(int(2.0 * FPS)):
        fr = blurbg(im, 0.35); stripes(fr, k); d = ImageDraw.Draw(fr, 'RGBA')
        s = int(100 + 20 * ease(k / 8))
        ctext(d, 560, "OQ BO'RILAR", s + 20, fill='white', stroke=4)
        ctext(d, 730, 'MUXLISLARI', s, fill='#111', box=YEL)
        ctext(d, 940, "qo'l ko'taring!", 72, fill='white', b=BOLD)
        v.add(fr)
    for k in range(int(4.2 * FPS)):
        fr = blurbg(im, 0.45); stripes(fr, 30); s = 1.0 + 0.10 * k / (4.2 * FPS)
        pp = fit(im, 1000, 1240, s); fr.paste(pp, ((W - pp.width) // 2, 360 - (pp.height - 1240) // 2))
        d = ImageDraw.Draw(fr, 'RGBA')
        ctext(d, 200, "Tarixiy 2026 — devoringizda", 64, fill='#111', box=YEL)
        if k > FPS * 1.2:
            a = ease((k - FPS * 1.2) / 8); sz = int(60 + 30 * a)
            ctext(d, 1640, "200 000 so'm", sz, fill='#111', box=YEL)
        v.add(fr)
    for k in range(int(2.2 * FPS)):
        fr = blurbg(gerb, 0.45); stripes(fr, 30); pp = fit(gerb, 1000, 1180, 1.0 + 0.06 * k / FPS)
        fr.paste(pp, ((W - pp.width) // 2, 400 - (pp.height - 1180) // 2)); d = ImageDraw.Draw(fr, 'RGBA')
        ctext(d, 200, "Vatanparvar sovg'a", 72, fill='#111', box=YEL)
        ctext(d, 1640, "O'zbekiston gerbi soati", 60, fill='white', box=(0, 0, 0, 180))
        v.add(fr)
    endcard(v, 2.4, "Buyurtma bir daqiqada:", '@Metart_shop_bot', "O'zbekiston bo'ylab yetkazamiz")
    v.close()

if __name__ == '__main__':
    which = sys.argv[2:] or ['logo', 'klub', 'borilar']
    if 'logo' in which: reel_logo()
    if 'klub' in which: reel_klub()
    if 'borilar' in which: reel_borilar()
