# 成層圏音響計測システム README

**KOSEN3 DevKit - 録音 & FFT解析プログラム**

---

## 概要

このパッケージには以下の2つのスクリプトが含まれています。

1. `recorder.py` ... Raspberry Pi上で録音・ブザー制御を行うメインプログラム
2. `fft_stratosphere_sound.py` ... 録音済みWAVファイルをFFT解析してCSV出力するプログラム

---

## 1. recorder.py

### 概要

Raspberry Pi上で動作する録音プログラム。
マイク（voicehat）から音声を取得しながら、パッシブブザーで定期的に既知周波数のトーンを鳴らし、チャンクごとにWAVファイルとして保存します。
成層圏気球実験において、音響環境の記録と参照トーンの埋め込みを同時に行うことを目的としています。

### 動作環境

- **ハードウェア**: Raspberry Pi Zero 2 W
- **マイク**: SPH0645LM4H搭載 I2S MEMSマイクモジュール
- **Pythonパッケージ**:
  - pigpio
  - sounddevice
  - soundfile
  - numpy

### 設定パラメータ（スクリプト冒頭）

| パラメータ | 説明 | デフォルト値 |
|---|---|---|
| `TOTAL_SECONDS` | 録音総時間 [秒] | 7200（2時間） |
| `SILENT_SECONDS` | 1サイクルの無音時間 [秒] | 6 |
| `FREQ` | ブザーで鳴らす周波数リスト | [1000, 2000, 3000, 4000] Hz |
| `CYCLE_SECONDS` | 1サイクルの長さ | `SILENT_SECONDS + len(FREQ)` = 10秒 |
| `CHUNK_SECONDS` | WAVファイル1個の長さ [秒] | 60（1分） |
| `BUZZER_PIN` | GPIOピン番号 | 12 |
| `DUTY` | PWMデューティ比 | 50000（50%） |
| `SAVE_DIR` | 保存先ディレクトリ | `/home/pi/kosen3-devkit/recording-mission` |
| `FS` | サンプリング周波数 [Hz] | 48000 |

### 録音サイクルの仕組み

1サイクル = 10秒:

```
[0〜6秒]  無音（環境音のみ録音）
[6秒]     1000 Hz トーン 1秒
[7秒]     2000 Hz トーン 1秒
[8秒]     3000 Hz トーン 1秒
[9秒]     4000 Hz トーン 1秒
```

これを `TOTAL_SECONDS // CYCLE_SECONDS = 720サイクル` 繰り返します。

### 出力ファイル

- **保存先**: `SAVE_DIR`
- **ファイル名**: `chunk_YYYYMMDD_HHMMSS_NNN.wav`
  - `YYYYMMDD_HHMMSS`: プログラム起動日時
  - `NNN`: チャンク番号（000, 001, ...）
- **フォーマット**: PCM 32bit, 48000 Hz, モノラル
- 1ファイルあたり60秒（約11 MB相当）、合計120ファイル

### 実行方法

```bash
# pigpiod の起動が必要
sudo pigpiod
python3 recorder.py
```

### 注意事項

- pigpiodが起動していないと接続エラーになります
- voicehatデバイスが見つからない場合は `RuntimeError` が発生します
- 保存先ディレクトリ（`SAVE_DIR`）は事前に作成しておいてください
  ```bash
  mkdir -p /home/pi/kosen3-devkit/recording-mission
  ```

---

## 2. fft_stratosphere_sound.py

### 概要

`recorder.py` で録音・結合されたWAVファイルを読み込み、埋め込みトーン部分をFFT解析して各周波数のdB値をCSV形式で出力します。

### 動作環境

- **Pythonパッケージ**:
  - numpy
  - pandas
  - soundfile

### 設定パラメータ（スクリプト冒頭）

| パラメータ | 説明 | デフォルト値 |
|---|---|---|
| `WAV_PATH` | 入力WAVファイルのパス | `"data_combined_13.wav"` |
| `CYCLE` | 1サイクルの長さ [秒] | 10.0 |
| `FREQS` | 解析対象の周波数リスト [Hz] | [1000, 2000, 3000, 4000] |
| `F_TOL` | 周波数トレランス（±Hz） | 80.0 |
| `EDGE` | トーン区間の端を除外する秒数 | 0.05（立ち上がり・立ち下がり除去） |

### 解析の仕組み

WAVファイル全体をCYCLE秒ごとのブロックに分割し、各ブロック内のトーン区間（EDGE秒を除いた部分）に対してFFTを実行します。

各サイクルの解析区間（例: サイクル `i`、`t0 = i × 10.0`）:

| 周波数 | 区間 |
|---|---|
| 1000 Hz | t0 + 6.05 〜 t0 + 6.95 秒 |
| 2000 Hz | t0 + 7.05 〜 t0 + 7.95 秒 |
| 3000 Hz | t0 + 8.05 〜 t0 + 8.95 秒 |
| 4000 Hz | t0 + 9.05 〜 t0 + 9.95 秒 |

各区間にハニング窓をかけてrFFTを実行し、対象周波数 ± `F_TOL` Hz の範囲の平均振幅をdBに変換します。

```
dB値 = 20 × log10(平均振幅 + 1e-12)
```

### 入力ファイル

- `recorder.py` で生成したチャンクWAVを別途 `merge.py` 等で結合したもの
- 命名規則例: `data_combined_13.wav`
- フォーマット: PCM 32bit, 48000 Hz, モノラル（`recorder.py` の出力と一致すること）

### 出力ファイル

- **ファイル名**: `data_combined_13_fft.csv`（入力ファイル名に `_fft` を付加）
- **エンコーディング**: UTF-8 BOM付き（Excelで直接開ける）

**フォーマット例**:

```
set, 1kHz, 2kHz, 3kHz, 4kHz
1, -23.45, -21.12, -25.67, -28.90
2, -22.88, -20.55, -24.11, -27.43
...
```

※ `set` 列はサイクル番号（1始まり）

### 実行方法

```bash
# WAV_PATHを適宜書き換えてから実行
python3 fft_stratosphere_sound.py
```

### 注意事項

- `WAV_PATH` は実際のファイル名に合わせて変更してください
- 入力WAVの長さがCYCLE未満の場合、出力は0行になります
- 録音チャンクを結合せずに単体で入力した場合も動作しますが、サイクル番号はそのファイル内での通し番号になります

---

## ワークフロー全体

**[Raspberry Pi 上]**

1. `sudo pigpiod`
2. `python3 recorder.py`
   → `chunk_YYYYMMDD_HHMMSS_000.wav`, `chunk_YYYYMMDD_HHMMSS_001.wav`, ... , `chunk_YYYYMMDD_HHMMSS_119.wav`

**[PCへ転送後]**

3. `merge.py` 等でチャンクを結合
   → `data_combined_XX.wav`

4. `fft_stratosphere_sound.py` の `WAV_PATH` を書き換えて実行
   → `data_combined_XX_fft.csv`

5. CSVをExcelで開いてグラフ等で解析

---

## ファイル一覧

| ファイル | 説明 |
|---|---|
| `recorder.py` | 録音 & ブザー制御（Raspberry Pi用） |
| `fft_stratosphere_sound.py` | FFT解析 & CSV出力（PC用） |
| `README.md` | このファイル |

---

作成: 12Group
