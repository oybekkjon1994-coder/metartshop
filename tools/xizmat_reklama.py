"""Metall xizmatlari reklama videosi — haqiqiy lazer kadrlari + xizmat kartalari + vizitka."""
import os, sys, math, subprocess
from PIL import Image, ImageOps, ImageDraw, ImageFilter
sys.argv=[sys.argv[0], 'src/noyabr']; sys.path.insert(0,'tools')
import noyabr_reels as R

def card(v, name, sub, dur=2.6):
    """Toza xizmat kartasi — to'q fon, to'q sariq aksent, markazda xizmat nomi."""
    n=int(dur*R.FPS)
    for k in range(n):
        fr=Image.new('RGB',(R.W,R.H),(14,18,20)); d=ImageDraw.Draw(fr)
        # orqa fon naqshi — xira chiziqlar
        for gy in range(0,R.H,120): d.line((0,gy,R.W,gy),fill=(22,27,30),width=2)
        a=R.ease(min(1,k/6))
        # chap to'q sariq ustun
        d.rectangle((0,R.H//2-260,24,R.H//2+260),fill=R.YEL)
        # xizmat nomi
        sz=int(96+10*a)
        R.ctext(d, R.H//2-150, name, sz, fill='white')
        R.ctext(d, R.H//2+20, sub, 52, fill=R.YEL, b=R.BOLD)
        # pastda brend
        R.ctext(d, R.H-360, 'METARTSHOP', 46, fill=(150,150,150), b=R.BOLD)
        R.ctext(d, R.H-290, 'Toshkent', 40, fill=(110,110,110), b=R.BOLD)
        v.add(fr)

v=R.Video('v8-xizmat-reklama')
# 1) ochilish — lazer kesish
R.clip(v,'uchqun_hd.mp4' if os.path.exists(R.src('uchqun_hd.mp4')) else 'kesish3.mp4',2,3.2,top='Metallga ishlov',top2='berish — Toshkent',vol=0.5)
# 2) lazer xizmatlari — haqiqiy kadr ustida
R.clip(v,'kesish3.mp4',6,3.0,label='Lazer kesish',vol=0.5)
R.clip(v,'kesish1.mp4',3,3.0,speed=0.6,label='Listogib — bukish',vol=0.5)
# 3) svarka va bo'yoq — toza matnli karta (kadr yo'q)
card(v,'Kempi svarka','Sifatli payvand')
card(v,'Kukun bo‘yoq','Chidamli rang · parashkavoy')
# 4) vizitka — oxirida 4 soniya
im=ImageOps.exif_transpose(Image.open(R.src('vizitka.jpg'))).convert('RGB')
bg=ImageOps.fit(im,(R.W,R.H)).filter(ImageFilter.GaussianBlur(40)).point(lambda x:int(x*0.5))
s=min(R.W/im.width,R.H/im.height); fg=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
frame=bg.copy(); frame.paste(fg,((R.W-fg.width)//2,(R.H-fg.height)//2))
for _ in range(int(4.0*R.FPS)): v.add(frame)
v.close(bpm=112)
print('tayyor')
