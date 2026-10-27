"""1080x1920 story kartochkalari (k1-mancity uslubida).
python3 tools/story_cards.py tools/stories-h02.json -> stories/<id>.jpg
JSON: [{"id","src","title","price"(ixtiyoriy),"sub","white"(ixtiyoriy),"size"(sarlavha o'lchami)}]"""
import json,sys,os
from PIL import Image,ImageOps,ImageFilter,ImageDraw,ImageFont
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W,H=1080,1920;FD='/usr/share/fonts/opentype/inter/'
F=lambda n,s:ImageFont.truetype(FD+n,s)
def load(p):
    rot=p.startswith('@');p=p.lstrip('@')
    im=ImageOps.exif_transpose(Image.open(os.path.join(ROOT,p))).convert('RGB')
    return im.rotate(90,expand=True) if rot else im
def wrap(d,t,f,mw):
    out=[]
    for para in t.split('\n'):
        line=''
        for w in para.split():
            tl=(line+' '+w).strip()
            if d.textlength(tl,font=f)>mw and line: out.append(line);line=w
            else: line=tl
        out.append(line)
    return out
def card(c):
    im=load(c['src'])
    if c.get('white'):
        im=im.crop(ImageOps.invert(im.convert('L')).getbbox());bg=Image.new('RGB',(W,H),'#151515')
        pad=Image.new('RGB',(im.width+80,im.height+80),'white');pad.paste(im,(40,40));im=pad
    else:
        bg=ImageOps.fit(im,(W,H)).filter(ImageFilter.GaussianBlur(40)).point(lambda v:int(v*.35))
    s=min(W/im.width,1150/im.height);p=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS)
    bg.paste(p,((W-p.width)//2,170+(1150-p.height)//2))
    g=Image.new('L',(1,H));[g.putpixel((0,y),int(255*min(1,max(0,(y-900)/650))**1.4*.92)) for y in range(H)]
    bg=Image.composite(Image.new('RGB',(W,H),'#0b0b0b'),bg,g.resize((W,H)))
    top=Image.new('L',(1,H));[top.putpixel((0,y),int(200*max(0,1-y/260))) for y in range(H)]
    bg=Image.composite(Image.new('RGB',(W,H),'#0b0b0b'),bg,top.resize((W,H)))
    d=ImageDraw.Draw(bg)
    d.text((62,92),'@metart_shop',font=F('Inter-Medium.otf',34),fill='white')
    f=F('Inter-Medium.otf',34);t='METARTSHOP';d.text((W-62-d.textlength(t,font=f),92),t,font=f,fill='#FFC21A')
    ft=F('InterDisplay-Black.otf',c.get('size',128));lines=wrap(d,c['title'].upper() if c.get('upper',True) else c['title'],ft,W-124)
    lh=int(c.get('size',128)*1.0);y=H-370-len(lines)*lh-(140 if c.get('price') else 20)
    for i,l in enumerate(lines): d.text((58,y+i*lh),l,font=ft,fill='white')
    y+=len(lines)*lh+30
    if c.get('price'):
        fp=F('InterDisplay-Black.otf',78);t=c['price'];w=d.textlength(t,font=fp)
        d.rounded_rectangle((60,y,60+w+76,y+104),52,fill='#FFC21A');d.text((98,y+8),t,font=fp,fill='#0b0b0b');y+=140
    if c.get('sub'): d.text((62,y),c['sub'],font=F('Inter-Regular.otf',32),fill='#bdbdbd');y+=60
    fb=F('Inter-SemiBold.otf',42);d.text((62,y),'Buyurtma bot: ',font=fb,fill='white')
    d.text((62+d.textlength('Buyurtma bot: ',font=fb),y),'@Metart_shop_bot',font=fb,fill='#FFC21A');y+=58
    d.text((62,y),'+998 77 017 99 90',font=F('Inter-Medium.otf',40),fill='#FFC21A')
    out=os.path.join(ROOT,'stories',c['id']+'.jpg');bg.save(out,quality=88);return out
if __name__=='__main__':
    for c in json.load(open(sys.argv[1])): print(card(c))
