import numpy as np
import pandas as pd
import soundfile as sf
import math

WAV_PATH = "data_combined_13.wav"

CYCLE = 10.0
FREQS = [1000, 2000, 3000, 4000]
F_TOL = 80.0
EDGE = 0.05

def read_segment(wav, sr, a, b):
    s = int(a * sr)
    e = int(b * sr)
    wav.seek(s)
    x = wav.read(e - s, dtype="float32", always_2d=True)
    return x.mean(axis=1)

def fft_db(x, sr, f0):
    if len(x) == 0:
        return float("nan")
    w = np.hanning(len(x))
    X = np.fft.rfft(x * w)
    mag = np.abs(X)
    f = np.fft.rfftfreq(len(x), 1/sr)

    m = (f >= f0 - F_TOL) & (f <= f0 + F_TOL)
    v = np.mean(mag[m])
    return 20 * math.log10(v + 1e-12)

rows = []

with sf.SoundFile(WAV_PATH) as wav:
    sr = wav.samplerate
    total = wav.frames / sr
    n = int(total // CYCLE)

    for i in range(n):
        t0 = i * CYCLE

        row = {"set": i+1}

        for j, f0 in enumerate(FREQS):
            a = t0 + 6 + j + EDGE
            b = t0 + 6 + j + 1 - EDGE

            x = read_segment(wav, sr, a, b)
            row[f"{f0//1000}kHz"] = fft_db(x, sr, f0)

        rows.append(row)

pd.DataFrame(rows).to_csv("data_combined_13_fft.csv", index=False, encoding="utf-8-sig")
print("data_combined_13_fft.csv")