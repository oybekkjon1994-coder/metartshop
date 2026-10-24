const fs=require('fs');const d=require('../src/design');
(async()=>{for(const [f,c] of [['logo_alpha.png','qora'],['logo_white.jpg','oltin'],['fcb.jpg','qora'],['rm.jpg','oq']].filter(([f])=>fs.existsSync(__dirname+'/'+f))){
 const t=Date.now();const s=await d.makeShape(fs.readFileSync(__dirname+'/'+f));
 fs.writeFileSync(__dirname+'/out_'+f+'.jpg',await d.makePreview(s,c,'40 sm · '+c));
 const x=await d.makeDxf(s,400);fs.writeFileSync(__dirname+'/out_'+f+'.dxf',x.dxf);
 console.log(f,x.contours,'kontur',x.widthMm+'x'+x.heightMm,'mm, kesish',d.cutLength(x.dxf).toFixed(2),'m',Date.now()-t,'ms');}})().catch(e=>{console.error(e);process.exit(1)});
