import numpy as np,wave,subprocess,math,sys,json
from PIL import Image,ImageFilter,ImageOps,ImageDraw,ImageFont
W,H,FPS,SR=1080,1920,30,44100
FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
import os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
U=ROOT+'/';S=ROOT+'/img/'
def font(s): return ImageFont.truetype(FB,s)
def load(p):
    rot=0
    if p.startswith('@'): rot,p=90,p[1:]
    im=ImageOps.exif_transpose(Image.open(p if p.startswith('/') else U+p)).convert('RGB')
    return im.rotate(rot,expand=True) if rot else im
def wrap(d,t,f,maxw):
    out=[]
    for para in t.split('\n'):
        line=''
        for w in para.split():
            tl=(line+' '+w).strip()
            if d.textlength(tl,font=f)>maxw and line: out.append(line);line=w
            else: line=tl
        out.append(line)
    return out
def text(d,y,t,size,fill='white',box='#000000b0'):
    f=font(size)
    for i,line in enumerate(wrap(d,t,f,W-140)):
        w=d.textlength(line,font=f);x=(W-w)/2;yy=y+i*int(size*1.3)
        if box: d.rounded_rectangle((x-26,yy-14,x+w+26,yy+size+18),20,fill=box)
        d.text((x,yy),line,font=f,fill=fill)
def clip(src,dur,top=None,bot=None,small=None,white=False,z=(1.0,1.07)):
    im=load(src)
    if white:
        bg=Image.new('RGB',(W,H),'white');im=im.crop(ImageOps.invert(im.convert('L')).getbbox())
    else:
        bg=ImageOps.fit(im,(W,H)).filter(ImageFilter.GaussianBlur(50)).point(lambda v:int(v*0.5))
    s0=min((W-60)/im.width,(H*0.6)/im.height)
    n=int(dur*FPS)
    for k in range(n):
        s=s0*(z[0]+(z[1]-z[0])*k/max(1,n-1))
        fr=bg.copy();p=im.resize((int(im.width*s),int(im.height*s)),Image.BILINEAR)
        fr.paste(p,((W-p.width)//2,(H-p.height)//2+30))
        d=ImageDraw.Draw(fr,'RGBA');fc='#111' if white else 'white';bx=None if white else '#000000b0'
        if top: text(d,180,top,66,fc,bx)
        if bot: text(d,H-440,bot,52,fc,bx)
        if small: text(d,H-300,small,40,'#555' if white else '#FFE600',bx)
        yield fr
def endcard(dur,line1):
    n=int(dur*FPS)
    for k in range(n):
        fr=Image.new('RGB',(W,H),'#111');d=ImageDraw.Draw(fr)
        r=310+int(10*math.sin(k/6));cx,cy=W//2,680
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill='#FFE600')
        for t,sz,yy in [('METART',116,cy-105),('S  H  O  P',54,cy+40)]:
            f=font(sz);w=d.textlength(t,font=f);d.text((cx-w/2,yy),t,font=f,fill='#111')
        for i,(t,s,c) in enumerate([(line1,50,'white'),('Direct yoki Telegram',50,'white'),('@lazekametal',64,'#FFE600'),("O'zbekiston bo'ylab yetkazib berish",36,'#bbb'),('Доставка по всему Узбекистану',36,'#bbb')]):
            f=font(s);w=d.textlength(t,font=f);d.text(((W-w)/2,1150+i*95),t,font=f,fill=c)
        yield fr
def beat(D,seed,cuts):
    rng=np.random.default_rng(seed);N=int(SR*D);L=np.zeros(N);R=np.zeros(N)
    def add(sig,t,pan=0,g=1):
        i=int(t*SR);j=min(N,i+len(sig))
        if i>=N or i<0: return
        L[i:j]+=sig[:j-i]*g*(1-max(0,pan));R[i:j]+=sig[:j-i]*g*(1+min(0,pan))
    T=lambda d:np.arange(int(d*SR))/SR
    kick=lambda:(lambda t:np.sin(2*np.pi*np.cumsum(50+120*np.exp(-t*30))/SR)*np.exp(-t*9))(T(.35))
    snare=lambda:(lambda t:(rng.standard_normal(len(t))*.7+np.sin(2*np.pi*190*t)*.5)*np.exp(-t*18))(T(.22))
    def hat(o=False):
        t=T(.18 if o else .05);n=np.diff(np.concatenate([[0],rng.standard_normal(len(t))]));return n*np.exp(-t*(15 if o else 70))*.35
    def bass(f,d):
        t=T(d);return (np.sign(np.sin(2*np.pi*f*t))*.5+np.sin(2*np.pi*f*t))*np.minimum(1,t*80)*np.exp(-t*2.5)*.33
    def pluck(f,d=.25):
        t=T(d);return (np.sin(2*np.pi*f*t)+.4*np.sin(4*np.pi*f*t))*np.exp(-t*12)*.2
    def riser(d):
        t=T(d);f=200+1800*(t/d)**2;return (rng.standard_normal(len(t))*.25+np.sin(2*np.pi*np.cumsum(f)/SR)*.2)*(t/d)**2
    def impact():
        t=T(1.2);return (np.sin(2*np.pi*np.cumsum(40+60*np.exp(-t*8))/SR)+rng.standard_normal(len(t))*.3*np.exp(-t*12))*np.exp(-t*3.5)
    keys=[[110,110,87.31,98],[98,98,77.78,87.31],[123.47,98,110,92.5],[103.83,87.31,77.78,92.5]]
    roots=keys[seed%4];mel=[r*8 for r in roots]
    bpm=[120,124,128,116][seed%4];B=60/bpm;c0=cuts[0]
    for k,f in enumerate(mel): add(pluck(f,.4),max(0,c0-2+k*B),pan=.3*(-1)**k,g=.8)
    add(riser(min(2,c0)),max(0,c0-2));add(impact(),c0)
    n=0;t=c0
    while t<D-.5:
        add(kick(),t,g=.9)
        if n%2: add(snare(),t,g=.5)
        add(hat(),t+B/2,pan=.4);add(hat(n%4==3),t,pan=-.3,g=.7)
        add(bass(roots[(n//2)%4],B*.9),t)
        if n%2==0: add(pluck(mel[(n//2)%4]*2,.2),t+B/2,pan=-.4,g=.5)
        n+=1;t=c0+n*B
    for c in cuts[1:]: add(impact(),c,g=.55)
    m=np.stack([L,R],1);m/=np.abs(m).max()*1.12;fd=int(.4*SR);m[-fd:]*=np.linspace(1,0,fd)[:,None]
    w=wave.open('b.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes((m*32767).astype('<i2').tobytes());w.close()
def silent(D):
    import wave
    w=wave.open('b.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR);w.writeframes(b'\x00\x00\x00\x00'*int(SR*D));w.close()
def make(spec,seed):
    parts=[];cuts=[];t=0
    for i,c in enumerate(spec['clips']):
        d=c.get('d',2.4 if i==0 else 1.5);cuts.append(t+d if i==0 else t);parts.append(clip(c['src'],d,c.get('top'),c.get('bot'),c.get('small'),c.get('white',False)));t+=d
    cuts[0]=spec['clips'][0].get('d',2.4)
    parts.append(endcard(2.4,spec.get('end',"Buyurtma uchun:")));cuts.append(t);D=t+2.4
    silent(D)
    p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i','b.wav','-shortest','-c:v','libx264','-preset','medium','-crf','27','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-movflags','+faststart',f"out/{spec['id']}.mp4"],stdin=subprocess.PIPE)
    for g in parts:
        for fr in g: p.stdin.write(fr.tobytes())
    p.stdin.close();p.wait()
    # thumb
    subprocess.run(['ffmpeg','-y','-loglevel','error','-ss','1.2','-i',f"out/{spec['id']}.mp4",'-frames:v','1','-vf','scale=216:-1',f"out/{spec['id']}.png"])
if __name__=='__main__':
    specs=json.load(open(sys.argv[1]));os.makedirs('out',exist_ok=True)
    for i,s in enumerate(specs):
        
        make(s,i);print(s['id'],flush=True)
