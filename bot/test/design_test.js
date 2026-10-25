const fs=require('fs');const d=require('../src/design');
// Har bir siluet BITTA bo'lak bo'lishi kerak (lazerda hech narsa tushib qolmasin)
function parts(mask,S){const seen=new Uint8Array(S*S);let n=0;const q=new Int32Array(S*S);
 for(let i=0;i<S*S;i++){if(!mask[i]||seen[i])continue;n++;let h=0,t=0;q[t++]=i;seen[i]=1;
  while(h<t){const p=q[h++],x=p%S;for(const k of [x>0?p-1:-1,x<S-1?p+1:-1,p-S,p+S])if(k>=0&&k<S*S&&mask[k]&&!seen[k]){seen[k]=1;q[t++]=k;}}}
 return n;}
(async()=>{let bad=0;
 const files=[['logo_alpha.png','qora'],['logo_white.jpg','oltin'],['fcb.jpg','qora'],['rm.jpg','oq']].filter(([f])=>fs.existsSync(__dirname+'/'+f));
 for(const [f,c] of files){
  const s=await d.makeShape(fs.readFileSync(__dirname+'/'+f));
  fs.writeFileSync(__dirname+'/out_'+f+'.jpg',await d.makePreview(s,c,'40 sm · '+c));
  const x=await d.makeDxf(s,300);fs.writeFileSync(__dirname+'/out_'+f+'.dxf',x.dxf);
  const p=parts(s.mask,s.S);
  console.log(f,'bo\'laklar:',p,'kontur:',x.contours,x.widthMm+'x'+x.heightMm,'mm','ingichka:',x.thin||'yo\'q');
  if(p!==1||x.contours<1||!/CIRCLE/.test(x.dxf))bad++;}
 if(!files.length){console.log('rasm topilmadi');process.exit(1);}
 process.exit(bad?1:0);})().catch(e=>{console.error(e);process.exit(1)});
