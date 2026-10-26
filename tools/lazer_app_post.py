"""Lazer ustaxona ilovasi uchun tushunarli karusel (1080x1350) va Reels (1080x1920).
python3 tools/lazer_app_post.py <skrinshotlar_papkasi>"""
import sys, os, math, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); SRC = sys.argv[1]
BLACK = '/usr/share/fonts/opentype/inter/InterDisplay-Black.otf'; BOLD = '/usr/share/fonts/opentype/inter/InterDisplay-Bold.otf'
ORANGE = (255, 106, 0); DARK = (22, 22, 26); YEL = (255, 194, 26)
_F = {}
def font(s, b=BLACK):
    if (s, b) not in _F: _F[(s, b)] = ImageFont.truetype(b, s)
    return _F[(s, b)]
def ease(t): t = max(0, min(1, t)); return t * t * (3 - 2 * t)

def phone(shot, w=520, *_):
    """Telefon ramkasi ichida to'liq skrinshot."""
    im = Image.open(os.path.join(SRC, shot)).convert('RGB')
    sw = w - 36; sh = int(sw * im.height / im.width); scr = im.resize((sw, sh), Image.LANCZOS)
    H = sh + 36; out = Image.new('RGBA', (w, H), (0, 0, 0, 0)); d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, w - 1, H - 1), 62, fill=(18, 18, 20))
    m = Image.new('L', (sw, sh), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, sw - 1, sh - 1), 46, fill=255)
    out.paste(scr, (18, 18), m)
    d.rounded_rectangle((w / 2 - 70, 26, w / 2 + 70, 52), 13, fill=(18, 18, 20))
    return out

def shadow(img, r=30, op=110):
    a = img.split()[3].point(lambda v: op if v else 0)
    s = Image.new('RGBA', (img.width + 2 * r, img.height + 2 * r), (0, 0, 0, 0)); s.paste((0, 0, 0, 255), (r, r), a)
    return s.filter(ImageFilter.GaussianBlur(r / 2))

def wrap(d, text, f, maxw):
    lines = []
    for para in text.split('\n'):
        cur = ''
        for w in para.split():
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=f) > maxw and cur: lines.append(cur); cur = w
            else: cur = t
        lines.append(cur)
    return lines

SLIDES = [  # (sarlavha, kichik matn, skrinshot, scroll, raqam)
    ("Lazer ustasimisiz?", "Narxni qo'lda hisoblash, DXF chizish va listga joylashga soatlab vaqt ketyaptimi? Hammasi — bitta ilovada.", 'home.png', 0, None),
    ("DXF yuklang — narx darhol", "Kesish uzunligi, pirsing, o'lcham va qalinlik bo'yicha narxni o'zi hisoblaydi. Chizmadagi xatolarni ham topadi.", ('s1-narx.png', 's1b-narx.png'), 0, '1'),
    ("O'lchamdan DXF yasang", "Plastina, flanets, kosinka, darvoza, uy raqami... O'lchamni kiriting — tayyor DXF.", 's2-dxf.png', 0, '2'),
    ("Nesting: listga joylash", "Detallarni 1250×2500 listga o'zi joylaydi. Nechta list, qancha kesish, qancha chiqindi — darhol ko'rinadi.", ('s3-nest.png', 's3b-nest.png'), 0, '3'),
    ("Metall og'irligi va buyurtmalar", "List, truba, burchak, armatura og'irligi va narxi. Mijozlar, qarzlar va muddatlar — bitta daftarda.", ('s4-metal.png', 's5-buy.png'), 0, '4'),
]

CHIZISH = [
    ("DXF chizma chizishni bilmaysizmi?", "Bu ilova aynan siz uchun! AutoCAD ham, kompyuter ham shart emas — DXF ni telefonda chizasiz, 37 ta tayyor shablon bor.", 'd-list.png', 0, None),
    ("Naqsh tanlang", "Islomiy girih, jobiraka, kub, asalari uyasi... O'lchamni yozing — naqshli panel tayyor.", ('e-girihgal.png', 'd-girih.png'), 0, '1'),
    ("Kozirok paneli", "Old panel (yoy yoki friz) va yon kronshteyn. Eni, bo'yi, naqshi — bir necha soniyada.", 'd-kozirok.png', 0, '2'),
    ("Darvoza + 3D ko'rinish", "Darvoza va panjarani konstruktorda yig'asiz, mijozga 3D da rangi bilan ko'rsatasiz.", ('d-darvoza.png', 'e-3d.png'), 0, '3'),
    ("Logotip yoki rasmdan DXF", "Rasmni yuklang — ilova uni lazer kesadigan konturga aylantiradi.", ('e-rasm0.png', 'e-rasm.png'), 0, '4'),
    ("Yozuv va uy raqami", "Ism, firma nomi, ko'cha va uy raqami tablichkasi — shriftini tanlab, darhol DXF.", ('e-matn.png', 'd-uyraqam.png'), 0, '5'),
]
MODE = os.environ.get('MODE', 'ilova'); COVER = 4.6 if MODE == 'chizish' else 3.4
FX_T = [0.22, 19.15] if MODE == 'chizish' else []
BADGE = 'AutoCAD'; COVER = 4.6 if MODE == 'chizish' else 3.4
FX_T = [0.22, 19.15] if MODE == 'chizish' else []
BADGE = 'AutoCAD'
FEAT = ["Narx hisoblash", "DXF yasash (37 tayyor detal)", "Nesting — listga joylash", "Metall og'irligi va narxi", "Buyurtmalar daftari"]
NAME, REEL = 'lazer-ilova', 'v4-lazer-ilova'
if MODE == 'chizish':
    SLIDES = CHIZISH; NAME, REEL = 'lazer-chizish', 'v5-lazer-chizish'
    FEAT = ["DXF ni telefonda chizish", "37 ta shablon: naqsh, darvoza, kozirok", "Rasm va logotipdan DXF", "Darvozani 3D da ko'rsatish", "Narx, nesting, buyurtmalar"]

def slide(i, W=1080, H=1350, ph_w=500):
    title, sub, shot, scroll, num = SLIDES[i]
    bg = Image.new('RGB', (W, H), (245, 243, 238)); d = ImageDraw.Draw(bg)
    d.rectangle((0, 0, W, 14), fill=ORANGE)
    y = 70
    if num:
        d.ellipse((60, y, 160, y + 100), fill=ORANGE); f = font(64); w = d.textlength(num, font=f); d.text((110 - w / 2, y + 10), num, font=f, fill='white')
        tx = 190
    else: tx = 60
    for j, l in enumerate(wrap(d, title, font(66), W - tx - 60)): d.text((tx, y + 6 + j * 76), l, font=font(66), fill=DARK)
    ty = y + 6 + 76 * len(wrap(d, title, font(66), W - tx - 60)) + 20
    for j, l in enumerate(wrap(d, sub, font(34, BOLD), W - 120)): d.text((60, ty + j * 46), l, font=font(34, BOLD), fill=(90, 90, 96))
    nsub = len(wrap(d, sub, font(34, BOLD), W - 120)); top = ty + 46 * nsub + 40
    avail = H - 90 - 30 - top; shots = shot if isinstance(shot, tuple) else (shot,)
    pw = min(470, int((avail - 36) / 2.164) + 36)
    xs = [(W - pw) // 2] if len(shots) == 1 else [W // 2 - pw - 25, W // 2 + 25]
    for x, sh_ in zip(xs, shots):
        p = phone(sh_, pw); s = shadow(p); bg.paste(s, (x - 30, top - 10), s); bg.paste(p, (x, top), p)
    d = ImageDraw.Draw(bg); d.rectangle((0, H - 90, W, H), fill=DARK)
    d.text((60, H - 66), 'LAZER USTAXONA ilovasi', font=font(36), fill=YEL)
    t = '@lazer_uz77_bot'; d.text((W - 60 - d.textlength(t, font=font(36, BOLD)), H - 64), t, font=font(36, BOLD), fill='white')
    return bg

def price_slide(W=1080, H=1350):
    bg = Image.new('RGB', (W, H), DARK); d = ImageDraw.Draw(bg)
    def c(y, t, s, col='white', b=BLACK):
        f = font(s, b); d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=col)
    c(150, 'Narxi', 50, (180, 180, 186), BOLD)
    d.rounded_rectangle((150, 240, W - 150, 420), 40, fill=ORANGE); c(268, "449 000 so'm", 110)
    c(470, "Bir martalik to'lov", 54); c(545, "Oylik to'lov yo'q · Android", 40, (180, 180, 186), BOLD)
    for j, t in enumerate(FEAT):
        d.text((200, 660 + j * 70), '✓', font=font(46, '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'), fill=YEL); d.text((260, 664 + j * 70), t, font=font(40, BOLD), fill='white')
    d.rounded_rectangle((120, 1060, W - 120, 1190), 30, fill=YEL); c(1080, 'Sotib olish: @lazer_uz77_bot', 50, DARK)
    c(1230, "Telegram bot ilovani darhol yuboradi", 34, (180, 180, 186), BOLD)
    return bg

def karusel():
    os.makedirs(os.path.join(ROOT, 'ig'), exist_ok=True); paths = []
    for i in range(len(SLIDES)):
        p = os.path.join(ROOT, 'ig', f'{NAME}-{i + 1}.jpg'); slide(i).save(p, quality=92); paths.append(p)
    p = os.path.join(ROOT, 'ig', f'{NAME}-{len(SLIDES) + 1}.jpg'); price_slide().save(p, quality=92); paths.append(p)
    print(paths)

def reel():
    W, H, FPS = 1080, 1920, 30; out = os.path.join(ROOT, 'reels', REEL + '.mp4')
    pr = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                           '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    cnt = [0]
    def add(im):
        pr.stdin.write(fx(im.convert('RGB'), cnt[0] / FPS).tobytes()); cnt[0] += 1
    def center(d, y, t, s, col, b=BLACK):
        f = font(s, b); d.text(((W - d.textlength(t, font=f)) / 2, y), t, font=f, fill=col)
    for i, (title, sub, shot, scroll, num) in enumerate(SLIDES):
        shots = shot if isinstance(shot, tuple) else (shot,)
        n = int((COVER if i == 0 else 2.2 * len(shots) + 0.6) * FPS); phs = [phone(x, 600) for x in shots]; sh = shadow(phs[0])
        for k in range(n):
            t = k / (n - 1)
            if len(phs) == 1: p = phs[0]
            else:
                a = ease((t - 0.45) / 0.12); p = Image.blend(phs[0], phs[1], a) if 0 < a < 1 else phs[int(a >= 1)]
            bg = Image.new('RGB', (W, H), (245, 243, 238)); d = ImageDraw.Draw(bg)
            d.rectangle((0, 0, W, 16), fill=ORANGE)
            y = 120
            if num:
                d.ellipse((W / 2 - 60, y - 10, W / 2 + 60, y + 110), fill=ORANGE); center(d, y + 6, num, 78, 'white'); y += 140
            lines = wrap(d, title, font(76), W - 120)
            for j, l in enumerate(lines): center(d, y + j * 88, l, 76, DARK)
            y += 88 * len(lines) + 16
            for j, l in enumerate(wrap(d, sub, font(36, BOLD), W - 160)): center(d, y + j * 48, l, 36, (95, 95, 100), BOLD)
            off = int(260 * (1 - ease(k / 10))); top = max(y + 48 * 3 + 40, 600) + off
            bg.paste(sh, ((W - sh.width) // 2, top - 10), sh); bg.paste(p, ((W - p.width) // 2, top), p)
            add(bg)
    ps = price_slide(); big = Image.new('RGB', (W, H), DARK); big.paste(ps, (0, (H - ps.height) // 2))
    for k in range(int(3.6 * FPS)):
        fr = big.copy()
        if k < 8: fr = Image.blend(Image.new('RGB', (W, H), 'white'), fr, k / 8)
        add(fr)
    pr.stdin.close(); pr.wait()
    if MODE == 'chizish': add_music(out, cnt[0] / FPS)
    print(out)

def badge():
    f = font(170); w = int(ImageDraw.Draw(Image.new('L', (1, 1))).textlength(BADGE, font=f))
    im = Image.new('RGBA', (w + 140, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((10, 10, im.width - 10, im.height - 10), 50, fill=ORANGE, outline='white', width=12)
    d.text((70, 22), BADGE, font=f, fill='white')
    return im.rotate(-6, expand=True, resample=Image.BICUBIC)
_B = []

def fx(im, tt):
    for t0 in FX_T:
        dt = tt - t0
        if not 0 <= dt < 0.9: continue
        W, H = im.size
        z = 1 + 0.08 * (1 - ease(dt / 0.35))
        if z > 1.001:
            cw, ch = int(W / z), int(H / z); sx = int(10 * math.sin(dt * 90) * (1 - min(1, dt / 0.25)))
            x0 = (W - cw) // 2 + sx; y0 = (H - ch) // 2
            im = im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)
        if dt < 0.15: im = Image.blend(im, Image.new('RGB', (W, H), 'white'), 0.55 * (1 - dt / 0.15))
        if not _B: _B.append(badge())
        b = _B[0]
        sc = 1.18 * ease(dt / 0.16) if dt < 0.16 else 1.18 - 0.18 * ease((dt - 0.16) / 0.12)
        al = 1 - ease((dt - 0.6) / 0.3)
        if sc > 0.05 and al > 0:
            bb = b.resize((max(1, int(b.width * sc)), max(1, int(b.height * sc))), Image.BICUBIC)
            if al < 1: bb.putalpha(bb.split()[3].point(lambda v: int(v * al)))
            im = im.copy(); im.paste(bb, ((W - bb.width) // 2, int(H * 0.62) - bb.height // 2), bb)
    return im

def add_music(path, dur, db=-14):
    wav = path + '.wav'; subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'minus.py'), f'{dur:.2f}', wav], check=True)
    tmp = path + '.tmp.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-i', wav, '-filter_complex', f'[1:a]volume={db}dB[a]', '-map', '0:v', '-map', '[a]',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-shortest', tmp], check=True)
    os.replace(tmp, path); os.remove(wav)

def add_sfx(path, dur):
    parts, labels = [], []
    for i, t0 in enumerate(FX_T):
        ms = int(t0 * 1000)
        parts.append(f"anoisesrc=d=0.55:c=pink:a=0.6,highpass=f=400,lowpass=f=5000,afade=t=in:d=0.12,afade=t=out:st=0.12:d=0.4,adelay={ms}|{ms}[w{i}]")
        parts.append(f"sine=f=65:d=0.35,volume=1.6,afade=t=out:st=0.03:d=0.3,adelay={ms + 110}|{ms + 110}[b{i}]")
        labels += [f"[w{i}]", f"[b{i}]"]
    fc = ';'.join(parts) + ';' + ''.join(labels) + f"amix=inputs={len(labels)}:normalize=0,volume=0.8,apad=whole_dur={dur:.2f},atrim=0:{dur:.2f}[a]"
    tmp = path + '.tmp.mp4'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', path, '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '160k', '-ac', '2', '-shortest', tmp], check=True)
    os.replace(tmp, path)

if __name__ == '__main__':
    karusel(); reel()
