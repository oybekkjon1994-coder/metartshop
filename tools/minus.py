"""O'zimiz yasagan fon musiqasi (minus) — mualliflik huquqi muammosiz.
python3 tools/minus.py <davomiylik_s> <chiqish.wav> [bpm]"""
import sys, wave
import numpy as np

SR = 44100
dur = float(sys.argv[1]); out = sys.argv[2]; bpm = float(sys.argv[3]) if len(sys.argv) > 3 else 104
beat = 60 / bpm; N = int(dur * SR); mix = np.zeros((N, 2))
t_all = lambda d: np.arange(int(d * SR)) / SR
def put(sig, t0, pan=0.0, g=1.0):
    i = int(t0 * SR)
    if i >= N: return
    s = sig[:N - i] * g
    mix[i:i + len(s), 0] += s * (1 - max(0, pan)); mix[i:i + len(s), 1] += s * (1 + min(0, pan))

def kick():
    t = t_all(0.35); f = 50 + 90 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
def hat(open_=False):
    t = t_all(0.25 if open_ else 0.06); n = np.random.randn(len(t))
    n = np.diff(np.concatenate([[0], n]))  # yuqori chastota
    return n * np.exp(-t * (14 if open_ else 60)) * 0.25
def snare():
    t = t_all(0.22)
    return (np.random.randn(len(t)) * 0.5 + np.sin(2 * np.pi * 190 * t)) * np.exp(-t * 18) * 0.6
def note(f, d, kind='pad'):
    t = t_all(d)
    if kind == 'bass':
        s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
        env = np.minimum(1, t * 80) * np.exp(-t * 2.2)
    elif kind == 'pluck':
        s = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3))
        env = np.minimum(1, t * 200) * np.exp(-t * 7)
    else:
        s = sum(np.sin(2 * np.pi * f * (1 + dt) * t) for dt in (-0.004, 0, 0.004)) / 3
        env = np.minimum(1, t * 3) * np.minimum(1, (d - t) * 3)
    return s * env

hz = lambda m: 440 * 2 ** ((m - 69) / 12)
CH = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]  # Am F C G
bar = 4 * beat; nbars = int(dur / bar) + 1
for b in range(nbars):
    t0 = b * bar; root, tri = CH[b % 4]
    for m in tri: put(note(hz(m + 12), bar), t0, 0, 0.10)
    for k, off in enumerate((0, 1.5, 2, 3, 3.5)):
        put(note(hz(root - 12), beat * 0.9, 'bass'), t0 + off * beat, 0, 0.32)
    arp = tri + [tri[1] + 12]
    for k in range(8): put(note(hz(arp[k % 4] + 12), beat * 0.5, 'pluck'), t0 + k * beat / 2, (-0.4, 0.4)[k % 2], 0.06)
    for k in range(4):
        put(kick(), t0 + k * beat, 0, 0.55 if k % 2 == 0 else 0.4)
        if k % 2: put(snare(), t0 + k * beat, 0, 0.35)
    for k in range(8): put(hat(k % 4 == 3), t0 + k * beat / 2, 0.3, 0.6)

fade = int(1.5 * SR); mix[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))[:, None]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix = mix / np.max(np.abs(mix)) * 0.9
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
print(out)
