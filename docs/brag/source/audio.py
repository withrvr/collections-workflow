"""Synthesizes the soundtrack for brag.mp4: music and effects written as one piece.

A minor, 120 BPM, chords Am - F - C - G (one bar = 2s each). Effects use notes from
the same key and go through the same reverb bus as the pluck, so they sit in one space.
Writes music.wav (stereo, 48 kHz).
"""
import numpy as np
import wave

SR = 48000
DUR = 23.0
N = int(SR * DUR)
t_all = np.arange(N) / SR
rng = np.random.default_rng(7)

BEAT = 0.5
BAR = 2.0

def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)

# A minor: Am(A C E) F(F A C) C(C E G) G(G B D)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [45, 41, 48, 43]

def chord_at(t):
    return int(t // BAR) % 4

def env_adsr(n, a, d, s, r, sustain_len):
    """Linear ADSR, lengths in seconds; returns array of length n."""
    e = np.zeros(n)
    A, D, S, R = int(a * SR), int(d * SR), int(sustain_len * SR), int(r * SR)
    i = 0
    seg = [np.linspace(0, 1, max(A, 1)), np.linspace(1, s, max(D, 1)), np.full(max(S, 1), s), np.linspace(s, 0, max(R, 1))]
    for part in seg:
        k = min(len(part), n - i)
        if k <= 0:
            break
        e[i:i + k] = part[:k]
        i += k
    return e

def lowpass_fft(x, cutoff, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 / np.sqrt(1 + (f / cutoff) ** (2 * order))
    return np.fft.irfft(X, len(x))

def highpass_fft(x, cutoff, order=2):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X *= 1 - 1 / np.sqrt(1 + (f / cutoff) ** (2 * order))
    return np.fft.irfft(X, len(x))

def add(buf, start, sig, gain=1.0):
    i = int(start * SR)
    if i >= len(buf):
        return
    k = min(len(sig), len(buf) - i)
    buf[i:i + k] += sig[:k] * gain

def automation(points):
    """Piecewise-linear gain curve from [(time, gain), ...]."""
    ts, gs = zip(*points)
    return np.interp(t_all, ts, gs)

# ------------------------------------------------------------------ music
pad = np.zeros(N)
for b in range(int(DUR / BAR) + 1):
    start = b * BAR
    notes = CHORDS[b % 4]
    ln = BAR + 0.6
    n = int(ln * SR)
    tt = np.arange(n) / SR
    e = env_adsr(n, 0.5, 0.4, 0.8, 0.6, ln - 1.5)
    sig = np.zeros(n)
    for m in notes + [notes[0] + 12]:
        for det in (-0.12, 0.0, 0.12):  # three detuned saw-ish voices
            f = hz(m + det)
            ph = 2 * np.pi * f * tt + rng.uniform(0, 6.28)
            sig += (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.15 * np.sin(3 * ph))
    add(pad, start, sig * e / 14)
pad = lowpass_fft(pad, 1400)

bass = np.zeros(N)
for k in range(int(DUR / BEAT)):
    st = k * BEAT
    if st < 3.0:
        continue
    f = hz(ROOTS[chord_at(st)])
    n = int(0.48 * SR)
    tt = np.arange(n) / SR
    e = np.exp(-tt * 5) * np.minimum(1, tt / 0.008)
    sig = np.tanh(1.6 * np.sin(2 * np.pi * f * tt)) * e
    add(bass, st, sig * 0.32)
bass = lowpass_fft(bass, 500)

pluck = np.zeros(N)
ARP = [0, 1, 2, 3, 2, 1, 2, 3]  # index into chord + octave
for k in range(int(DUR / (BEAT / 2))):
    st = k * BEAT / 2
    if st < 3.0 or st > 22.0:
        continue
    ch = CHORDS[chord_at(st)] + [CHORDS[chord_at(st)][0] + 12]
    m = ch[ARP[k % 8]] + 12
    f = hz(m)
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    e = np.exp(-tt * 14) * np.minimum(1, tt / 0.003)
    sig = (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt) * np.exp(-tt * 30)) * e
    acc = 1.0 if k % 2 == 0 else 0.7
    add(pluck, st, sig * 0.11 * acc)

kick = np.zeros(N)
hats = np.zeros(N)
for k in range(int(DUR / BEAT)):
    st = k * BEAT
    in_groove = (7.0 <= st < 16.0) or (19.5 <= st < 22.0)
    if not in_groove:
        continue
    n = int(0.3 * SR)
    tt = np.arange(n) / SR
    fsweep = 45 + 90 * np.exp(-tt * 30)
    ph = 2 * np.pi * np.cumsum(fsweep) / SR
    add(kick, st, np.sin(ph) * np.exp(-tt * 9) * 0.36)
    # off-beat hat
    nh = int(0.06 * SR)
    noise = rng.standard_normal(nh) * np.exp(-np.arange(nh) / SR * 70)
    add(hats, st + BEAT / 2, noise * 0.022)
hats = lowpass_fft(highpass_fft(hats, 7000), 12000)

# ------------------------------------------------------------------ effects (same key, same space)
fx = np.zeros(N)

def blip(f, length=0.18, decay=28, bright=0.25):
    n = int(length * SR)
    tt = np.arange(n) / SR
    e = np.exp(-tt * decay) * np.minimum(1, tt / 0.002)
    return (np.sin(2 * np.pi * f * tt) + bright * np.sin(2 * np.pi * 2 * f * tt)) * e

def whoosh(length=0.6, peak=0.75):
    n = int(length * SR)
    tt = np.arange(n) / SR
    e = np.sin(np.pi * np.clip(tt / length, 0, 1)) ** 2
    e *= np.where(tt / length < peak, (tt / length) / peak, 1)
    return lowpass_fft(rng.standard_normal(n), 1800) * e

# hook: 13 red flashes, rising through A minor pentatonic
PENTA = [69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96, 98]
for k in range(13):
    add(fx, 0.9 + k * 0.08, blip(hz(PENTA[k]), 0.25, 22), 0.05)

# scene transitions: soft filtered air into each cut
for c in (3.0, 7.0, 12.4, 16.2, 19.6):
    add(fx, c - 0.45, whoosh(0.7), 0.035)

# file lands in the drop zone, then the Run click
n = int(0.25 * SR); tt = np.arange(n) / SR
add(fx, 5.6, np.sin(2 * np.pi * hz(45) * tt) * np.exp(-tt * 18), 0.22)
add(fx, 6.32, blip(hz(81), 0.08, 60, 0.6), 0.09)

# timeline stages tick in (control gate gets a minor-second "warning" note)
TL = [76, 79, 81, 82, 84, 88]
for i, m in enumerate(TL):
    add(fx, 7.55 + i * 0.32, blip(hz(m), 0.2, 26), 0.06 if i != 3 else 0.08)

# BLOCKED stamp: low A thud plus a filtered noise hit
n = int(0.9 * SR); tt = np.arange(n) / SR
thud = np.sin(2 * np.pi * (hz(33) + 40 * np.exp(-tt * 25)) * tt) * np.exp(-tt * 5)
thud += 0.5 * np.sin(2 * np.pi * hz(45) * tt) * np.exp(-tt * 6)
hit = lowpass_fft(rng.standard_normal(n), 900) * np.exp(-tt * 14)
add(fx, 9.5, thud * 0.42 + hit * 0.12)

# exception cards slide in
for i in range(7):
    add(fx, 12.65 + i * 0.22, blip(hz([69, 72, 76, 79, 76, 72, 69][i] + 12), 0.12, 40), 0.03)

# AI typing: very soft keys (kept in the background)
k_rng = np.random.default_rng(3)
tk = 16.6
while tk < 18.7:
    n = int(0.02 * SR)
    click = highpass_fft(np.pad(k_rng.standard_normal(n) * np.exp(-np.arange(n) / SR * 300), (0, 2000)), 2500)
    add(fx, tk, click, 0.018)
    tk += 0.055 + k_rng.uniform(0, 0.04)
# guard check line: a resolved major-sixth chime
for m in (76, 81, 85):
    add(fx, 18.6, blip(hz(m), 0.6, 6), 0.03)

# outro: swell into an A minor bloom
for m in (57, 64, 69, 72, 76):
    nn = int(3.2 * SR); tt = np.arange(nn) / SR
    e = np.minimum(1, tt / 0.04) * np.exp(-tt * 1.1)
    add(fx, 19.75, np.sin(2 * np.pi * hz(m) * tt) * e, 0.045)

# ------------------------------------------------------------------ shared reverb on pluck + fx
def reverb(x, seconds=1.8, wet=0.28):
    n = int(seconds * SR)
    tt = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-tt * 3.2)
    ir = lowpass_fft(ir, 5000)
    ir /= np.sqrt(np.sum(ir ** 2))
    L = len(x) + n
    nfft = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(ir, nfft), nfft)[:len(x)]
    return x * (1 - wet) + y * wet * 0.9

bus = reverb(pluck + fx)
pad_r = reverb(pad, 2.5, 0.35)

# ------------------------------------------------------------------ arrangement + mix
duck = automation([(0, 1), (9.45, 1), (9.52, 0.45), (10.4, 1), (DUR, 1)])
pad_g = automation([(0, 0.35), (2.5, 0.75), (16.2, 0.75), (16.6, 0.95), (19.4, 0.95), (19.7, 1.0), (DUR, 1.0)])
master = automation([(0, 0), (0.05, 1), (21.8, 1), (DUR, 0)])

music = pad_r * pad_g + bass + kick + hats
mix = music * duck + bus
mix *= master

left = mix + 0.004 * np.roll(mix, 240)
right = mix + 0.004 * np.roll(mix, 410)
st = np.stack([left, right], 1)
st = np.tanh(st * 1.2) / 1.2
st *= 0.89 / np.max(np.abs(st))

with wave.open("music.wav", "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype("<i2").tobytes())
print("wrote music.wav", st.shape[0] / SR, "s")
