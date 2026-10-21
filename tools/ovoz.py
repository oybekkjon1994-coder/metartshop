"""Reels videolarga o'zbekcha ovoz (diktor) qo'shadi.
GitHub Actions'da ishlaydi: python tools/ovoz.py tools/ovoz/<fayl>.json
JSON: {"voice":"uz-UZ-SardorNeural","rate":"+8%","items":[
  {"video":"reels/a.mp4","out":"reels/a-ovoz.mp4","lines":[[0.2,"Matn..."],[3.0,"..."]]}]}
Har bir gap o'z vaqtida boshlanadi; oldingisi tugamagan bo'lsa, ketidan keladi.
Ovoz video oxiridan oshsa, oxirgi kadr cho'ziladi."""
import asyncio, json, os, subprocess, sys, tempfile

import edge_tts


def dur(p):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                                          '-of', 'csv=p=0', p]).decode().strip())


async def tts(text, voice, rate, out):
    await edge_tts.Communicate(text, voice, rate=rate).save(out)


def main(spec_path):
    spec = json.load(open(spec_path, encoding='utf-8'))
    voice = spec.get('voice', 'uz-UZ-SardorNeural')
    rate = spec.get('rate', '+8%')
    for it in spec['items']:
        tmp = tempfile.mkdtemp()
        clips, t_end = [], 0.0
        for i, (t, text) in enumerate(it['lines']):
            mp3 = os.path.join(tmp, f'{i}.mp3')
            asyncio.run(tts(text, it.get('voice', voice), it.get('rate', rate), mp3))
            d = dur(mp3)
            start = max(float(t), t_end + 0.15 if clips else float(t))
            clips.append((start, mp3))
            t_end = start + d
            print(f"  {start:5.2f}-{t_end:5.2f}  {text}")
        vd = dur(it['video'])
        total = max(vd, t_end + 0.6)
        args = ['ffmpeg', '-y', '-loglevel', 'error', '-i', it['video']]
        for _, mp3 in clips:
            args += ['-i', mp3]
        fl = []
        for k, (start, _) in enumerate(clips):
            ms = int(start * 1000)
            fl.append(f"[{k+1}:a]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms},volume=1.6[a{k}]")
        mix = ''.join(f'[a{k}]' for k in range(len(clips)))
        fl.append(f"{mix}amix=inputs={len(clips)}:normalize=0,apad,atrim=0:{total:.2f}[aout]")
        vmap = '0:v'
        if total > vd + 0.05:
            fl.append(f"[0:v]tpad=stop_mode=clone:stop_duration={total - vd + 0.1:.2f},trim=0:{total:.2f}[vout]")
            vmap = '[vout]'
        args += ['-filter_complex', ';'.join(fl), '-map', vmap, '-map', '[aout]']
        args += (['-c:v', 'libx264', '-preset', 'medium', '-crf', '24', '-pix_fmt', 'yuv420p'] if vmap != '0:v'
                 else ['-c:v', 'copy'])
        args += ['-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-t', f'{total:.2f}', it['out']]
        subprocess.run(args, check=True)
        print('OK', it['out'], f'{dur(it["out"]):.1f}s')


if __name__ == '__main__':
    for p in sys.argv[1:]:
        main(p)
