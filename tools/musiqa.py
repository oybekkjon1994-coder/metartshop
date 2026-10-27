"""O'zimiz yaratadigan fon musiqasi — har xil uslub (mualliflik huquqi muammosiz).
python3 tools/musiqa.py <uslub> <davomiylik_s> <chiqish.wav>
uslublar: phonk, house, trap, lofi, sharq, pop"""
import sys, wave
import numpy as np

SR = 44100
style, dur, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
N = int(dur * SR); mix = np.zeros((N, 2)); rng = np.random.default_rng(7)
T = lambda d: np.arange(int(d * SR)) / SR
hz = lambda m: 440 * 2 ** ((m - 69) / 12)

def put(sig, t0, pan=0.0, g=1.0):
    i = int(t0 * SR)
    if i >= N or i < 0: return
    s = sig[:N - i] * g
    mix[i:i + len(s), 0] += s * (1 - max(0, pan)); mix[i:i + len(s), 1] += s * (1 + min(0, pan))

# ---- asboblar ----
def kick(hard=False):
    t = T(0.4); f = 45 + (160 if hard else 100) * np.exp(-t * (40 if hard else 30))
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (7 if hard else 9))
    return np.tanh(s * (3 if hard else 1.2))
def snare(): t = T(0.25); return (rng.standard_normal(len(t)) * 0.6 + np.sin(2 * np.pi * 185 * t)) * np.exp(-t * 16) * 0.6
def clap():
    t = T(0.3); n = rng.standard_normal(len(t)); env = np.exp(-t * 20)
    for d in (0.01, 0.02): env += np.roll(np.exp(-t * 60), int(d * SR)) * 0.6
    return n * env * 0.4
def hat(o=False):
    t = T(0.3 if o else 0.05); n = np.diff(np.concatenate([[0], rng.standard_normal(len(t))]))
    return n * np.exp(-t * (12 if o else 70)) * 0.22
def b808(f, d, slide_to=None):
    t = T(d); ff = np.full(len(t), f) if slide_to is None else f + (slide_to - f) * np.minimum(1, t / 0.12)
    s = np.sin(2 * np.pi * np.cumsum(ff) / SR); return np.tanh(s * 2.2) * np.minimum(1, t * 200) * np.exp(-t * 1.2) * 0.7
def cowbell(f, d=0.25):
    t = T(d); s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + np.sign(np.sin(2 * np.pi * f * 1.48 * t)) * 0.5
    return s * np.exp(-t * 9) * 0.25
def tone(f, d, kind='pad'):
    t = T(d)
    if kind == 'pad':
        s = sum(np.sin(2 * np.pi * f * (1 + dt) * t) for dt in (-0.005, 0, 0.005)) / 3; env = np.minimum(1, t * 3) * np.minimum(1, (d - t) * 3)
    elif kind == 'saw':
        s = sum(np.sin(2 * np.pi * f * k * t) / k for k in range(1, 8)); env = np.minimum(1, t * 100) * np.exp(-t * 2.5)
    elif kind == 'pluck':
        s = sum(np.sin(2 * np.pi * f * k * t) / k for k in (1, 2, 3)); env = np.minimum(1, t * 200) * np.exp(-t * 8)
    elif kind == 'piano':
        s = np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t) + 0.15 * np.sin(6 * np.pi * f * t); env = np.minimum(1, t * 300) * np.exp(-t * 3.5)
    elif kind == 'rhodes':
        s = np.sin(2 * np.pi * f * t + 1.5 * np.sin(2 * np.pi * f * t) * np.exp(-t * 4)); env = np.minimum(1, t * 100) * np.exp(-t * 1.6)
    elif kind == 'lead':
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.minimum(1, t * 3)
        s = np.sin(2 * np.pi * np.cumsum(f * vib) / SR) + 0.35 * np.sin(4 * np.pi * np.cumsum(f * vib) / SR); env = np.minimum(1, t * 40) * np.minimum(1, (d - t) * 20)
    elif kind == 'bass':
        s = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t); env = np.minimum(1, t * 80) * np.exp(-t * 2.2)
    elif kind == 'doira':
        s = np.sin(2 * np.pi * np.cumsum(90 + 120 * np.exp(-t * 50)) / SR) + rng.standard_normal(len(t)) * 0.3 * np.exp(-t * 40); env = np.exp(-t * 14)
    elif kind == 'tak':
        s = rng.standard_normal(len(t)) * 0.5 + np.sin(2 * np.pi * 420 * t); env = np.exp(-t * 45)
    return s * env

def chords(seq, bar, oct_=0, kind='pad', g=0.09, every=None):
    for b in range(int(dur / bar) + 2):
        for m in seq[b % len(seq)]:
            if every:
                for k in range(int(bar / every)): put(tone(hz(m + oct_), every * 0.95, kind), b * bar + k * every, 0, g)
            else: put(tone(hz(m + oct_), bar, kind), b * bar, 0, g)

def melody(notes, step, kind='lead', g=0.12, pan=0.0, start=0.0):
    t = start; i = 0
    while t < dur:
        m, l = notes[i % len(notes)]
        if m is not None: put(tone(hz(m), step * l * 0.95, kind), t, pan, g)
        t += step * l; i += 1

# ---- uslublar ----
if style == 'phonk':
    bpm = 140; b = 60 / bpm; bar = 4 * b
    for k in range(int(dur / (b / 2)) + 1):
        t0 = k * b / 2; pos = k % 8
        if pos in (0, 3, 6): put(kick(True), t0, 0, 0.6)
        if pos in (4,): put(clap(), t0, 0, 0.7)
        put(hat(), t0, 0.3, 0.5)
    cb = [(64, 1), (64, 1), (67, 1), (64, 1), (62, 1), (64, 1), (59, 2)] * 2 + [(64, 1), (67, 1), (69, 1), (67, 1), (64, 1), (62, 1), (60, 2)]
    t = 0; i = 0
    while t < dur:
        m, l = cb[i % len(cb)]; put(cowbell(hz(m + 12)), t, 0.15, 0.9); t += b / 2 * l; i += 1
    for bb in range(int(dur / bar) + 1):
        root = (40, 40, 36, 38)[bb % 4]; put(b808(hz(root), bar * 0.9, hz(root - 2) if bb % 2 else None), bb * bar, 0, 0.55)
elif style == 'house':
    bpm = 124; b = 60 / bpm; bar = 4 * b
    for k in range(int(dur / b) + 1):
        put(kick(), k * b, 0, 0.6); put(hat(True), k * b + b / 2, 0.25, 0.7)
        if k % 2: put(clap(), k * b, 0, 0.5)
    chords([[65, 68, 72], [61, 65, 68], [68, 72, 75], [63, 67, 70]], bar, 0, 'piano', 0.12, every=b * 1.5)
    for bb in range(int(dur / bar) + 1):
        root = (41, 37, 44, 39)[bb % 4]
        for k in range(8):
            if k % 2: put(tone(hz(root), b * 0.45, 'bass'), bb * bar + k * b / 2, 0, 0.35)
elif style == 'trap':
    bpm = 140; b = 60 / bpm; bar = 4 * b
    for k in range(int(dur / (b / 4)) + 1):
        t0 = k * b / 4; pos = k % 16
        if pos in (0, 10): put(kick(True), t0, 0, 0.55)
        if pos == 8: put(snare(), t0, 0, 0.7)
        if pos % 2 == 0 or (k // 16) % 2 and pos > 12: put(hat(), t0, 0.3, 0.45)
    chords([[57, 60, 64], [53, 57, 60], [55, 58, 62], [52, 56, 59]], bar, 12, 'pad', 0.07)
    melody([(81, 1), (None, 1), (79, 1), (76, 1), (None, 2), (77, 1), (76, 1)], b / 2, 'pluck', 0.12, -0.3)
    for bb in range(int(dur / bar) + 1):
        root = (33, 29, 31, 28)[bb % 4]; put(b808(hz(root), bar * 0.6), bb * bar, 0, 0.6); put(b808(hz(root), b, hz(root + 12)), bb * bar + 2.5 * b, 0, 0.4)
elif style == 'lofi':
    bpm = 84; b = 60 / bpm; bar = 4 * b; sw = b * 0.08
    for k in range(int(dur / (b / 2)) + 1):
        t0 = k * b / 2 + (sw if k % 2 else 0); pos = k % 8
        if pos in (0, 5): put(kick(), t0, 0, 0.45)
        if pos in (2, 6): put(snare(), t0, 0, 0.35)
        put(hat(), t0, 0.2, 0.35)
    chords([[62, 65, 69, 72], [55, 59, 62, 65, 69], [60, 64, 67, 71], [57, 60, 64, 67]], bar, 0, 'rhodes', 0.08)
    melody([(74, 1.5), (72, 0.5), (69, 2), (None, 1), (67, 1), (69, 1), (72, 1)], b, 'pluck', 0.06, 0.3, bar)
    mix += rng.standard_normal((N, 2)) * 0.004 * (rng.random((N, 1)) > 0.9995) * 40  # vinil chirsillashi
elif style == 'sharq':
    bpm = 104; b = 60 / bpm; bar = 4 * b
    pat = [('doira', 0), ('tak', 0.5), ('tak', 1.0), ('doira', 1.5), ('doira', 2), ('tak', 2.75), ('tak', 3.25), ('tak', 3.5)]
    for bb in range(int(dur / bar) + 1):
        for kind, off in pat: put(tone(0, 0.3, kind), bb * bar + off * b, 0.1 if kind == 'tak' else 0, 0.55 if kind == 'doira' else 0.25)
        put(kick(), bb * bar, 0, 0.4); put(kick(), bb * bar + 2 * b, 0, 0.4)
        root = (45, 45, 43, 44)[bb % 4]
        for off in (0, 1.5, 2, 3): put(tone(hz(root), b * 0.9, 'bass'), bb * bar + off * b, 0, 0.32)
    # garmonik minor (A): A B C D E F G#
    melody([(69, 1), (71, 0.5), (72, 0.5), (74, 1), (72, 0.5), (71, 0.5), (69, 1), (68, 1), (69, 2), (76, 1), (74, 0.5), (72, 0.5),
            (71, 1), (72, 0.5), (71, 0.5), (69, 1), (68, 0.5), (69, 1.5), (None, 2)], b, 'lead', 0.11, 0, bar)
    chords([[57, 60, 64], [57, 60, 64], [55, 59, 62], [56, 59, 64]], bar, 0, 'pad', 0.06)
else:  # pop
    bpm = 118; b = 60 / bpm; bar = 4 * b
    for k in range(int(dur / b) + 1):
        put(kick(), k * b, 0, 0.5 if k % 2 == 0 else 0.3)
        if k % 2: put(clap(), k * b, 0, 0.55)
        put(hat(), k * b + b / 2, 0.3, 0.5)
    chords([[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]], bar, 12, 'pluck', 0.08, every=b / 2)
    chords([[48], [43], [45], [41]], bar, 0, 'bass', 0.3, every=b / 2)
    melody([(72, 1), (74, 1), (76, 2), (79, 1), (76, 1), (74, 2), (72, 1), (74, 1), (76, 1), (74, 1), (72, 4)], b, 'lead', 0.09, 0, bar * 2)

fade = int(1.5 * SR); a = int(0.2 * SR)
mix[:a] *= np.linspace(0, 1, a)[:, None]; mix[-fade:] *= np.linspace(1, 0, fade)[:, None]
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.3) * 0.85
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
print(out)
