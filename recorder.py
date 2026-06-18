import pigpio
import threading
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
import queue
import time
import os

TOTAL_SECONDS = 7200
SILENT_SECONDS = 6
FREQ = [1000, 2000, 3000, 4000]
CYCLE_SECONDS = SILENT_SECONDS + len(FREQ)
CHUNK_SECONDS = 60
BUZZER_PIN = 12
DUTY = 50000
SAVE_DIR = "/home/pi/kosen3-devkit/recording-mission"
FS = 48000

DEVICE = None
for i, d in enumerate(sd.query_devices()):
    if "voicehat" in d["name"].lower() and d["max_input_channels"] > 0:
        DEVICE = i
        break
if DEVICE is None:
    raise RuntimeError("録音デバイスが見つかりません")

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CHUNK_PREFIX = f"{SAVE_DIR}/chunk_{TIMESTAMP}_"
SAMPLES_PER_CHUNK = FS * CHUNK_SECONDS
SAMPLES_TOTAL = FS * TOTAL_SECONDS

def main():
    pi = pigpio.pi()
    if not pi.connected:
        raise RuntimeError("pigpiodに接続できません")

    audio_q = queue.Queue()
    sample_counter = [0]

    def callback(indata, frames, time_info, status):
        audio_q.put(indata.copy())
        sample_counter[0] += frames

    stream = sd.InputStream(
        samplerate=FS, channels=1, dtype='int32',
        device=DEVICE, callback=callback, blocksize=1024
    )
    stream.start()

    buzzer_thread = threading.Thread(
        target=buzzer_loop, args=(pi, sample_counter), daemon=True
    )
    buzzer_thread.start()

    chunk_idx = 0
    chunk_buf = []
    chunk_samples = 0

    while sample_counter[0] < SAMPLES_TOTAL:
        try:
            data = audio_q.get(timeout=1)
        except queue.Empty:
            continue
        chunk_buf.append(data)
        chunk_samples += len(data)
        if chunk_samples >= SAMPLES_PER_CHUNK:
            combined = np.concatenate(chunk_buf)
            to_save = combined[:SAMPLES_PER_CHUNK]
            remainder = combined[SAMPLES_PER_CHUNK:]
            path = f"{CHUNK_PREFIX}{chunk_idx:03d}.wav"
            sf.write(path, to_save, FS, subtype='PCM_32')
            print(f"chunk {chunk_idx} saved")
            chunk_buf = [remainder] if len(remainder) > 0 else []
            chunk_samples = len(remainder)
            chunk_idx += 1

    if chunk_buf:
        combined = np.concatenate(chunk_buf)
        if len(combined) > 0:
            path = f"{CHUNK_PREFIX}{chunk_idx:03d}.wav"
            sf.write(path, combined, FS, subtype='PCM_32')

    stream.stop()
    stream.close()
    pi.hardware_PWM(BUZZER_PIN, 0, 0)
    pi.stop()
    buzzer_thread.join(timeout=2)
    print("録音完了")

def buzzer_loop(pi, sample_counter):
    cycle_samples = FS * CYCLE_SECONDS
    silent_samples = FS * SILENT_SECONDS
    tone_samples = FS * 1
    cycle = 0
    while True:
        cycle_start = cycle * cycle_samples
        if cycle_start >= SAMPLES_TOTAL:
            break
        wait_sample(sample_counter, cycle_start)
        pi.hardware_PWM(BUZZER_PIN, 0, 0)
        for j, f in enumerate(FREQ):
            tone_start = cycle_start + silent_samples + j * tone_samples
            if tone_start >= SAMPLES_TOTAL:
                break
            wait_sample(sample_counter, tone_start)
            pi.hardware_PWM(BUZZER_PIN, f, DUTY)
        cycle += 1
    pi.hardware_PWM(BUZZER_PIN, 0, 0)

def wait_sample(sample_counter, target):
    while sample_counter[0] < target:
        time.sleep(0.0005)

if __name__ == "__main__":
    main()
