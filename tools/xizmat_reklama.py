"""Metall xizmatlari reklama videosi — haqiqiy lazer kadrlari + vizitka."""
import os, sys, subprocess
from PIL import Image, ImageOps
sys.argv=[sys.argv[0], 'src/noyabr']; sys.path.insert(0,'tools')
import noyabr_reels as R
v=R.Video('v8-xizmat-reklama')
# 1) ochilish — lazer kesish
R.clip(v,'uchqun_hd.mp4' if os.path.exists(R.src('uchqun_hd.mp4')) else 'kesish3.mp4',2,3.2,top='Metallga ishlov',top2='berish — Toshkent',vol=0.5)
# 2) xizmatlar — kadr ustida ketma-ket
R.clip(v,'kesish3.mp4',6,3.0,label='Lazer kesish',vol=0.5)
R.clip(v,'kesish1.mp4',3,3.0,speed=0.6,label='Listogib — bukish',vol=0.5)
R.clip(v,'kesish2.mp4',2,3.0,label='Kempi svarka',vol=0.5)
R.clip(v,'mers_kesish.mp4',8,3.0,label='Kukun bo‘yoq',vol=0.5)
# 3) vizitka — oxirida 4 soniya
im=ImageOps.exif_transpose(Image.open(R.src('vizitka.jpg'))).convert('RGB')
bg=ImageOps.fit(im,(R.W,R.H)).filter(__import__('PIL.ImageFilter',fromlist=['GaussianBlur']).GaussianBlur(40)).point(lambda x:int(x*0.5))
s=min(R.W/im.width,R.H/im.height); fg=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
frame=bg.copy(); frame.paste(fg,((R.W-fg.width)//2,(R.H-fg.height)//2))
for _ in range(int(4.0*R.FPS)): v.add(frame)
v.close(bpm=112)
print('tayyor')
