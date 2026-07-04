"""
音声配信の正規化 (PREREGISTRATION §4「Audio delivery normalization」の実装)。

全エンジンに渡す音源を決定論の同一手順で標準化する:
  1. ピーク正規化: |peak| → 0.5 (-6 dBFS)。scale = 0.5 / peak (無音は不変)
  2. 16-bit PCM WAV で出力 (サンプルレート・チャンネルは不変)

根拠 (2026-07-04 パイロット batch 3 の発見):
  - FLEURS にはピーク -44 dBFS 級の極小音量マスタリングが混在する
  - Grok STT はそうした入力を無言で空転写にする (他エンジンは転写できる)
    → 未正規化レベルは「データセットのマスタリング癖」を測ってしまい、
      口述精度の測定と乖離する (実利用ではマイクAGCが利得を稼ぐ)
  - AmiVoice は float32 WAV を "unsupported audio format" で拒否する
    → PCM_16 配信で解消
  同一の正規化ファイルを全エンジンに送る。エンジン別の前処理は引き続き禁止。

Usage:
  python3 normalize_audio.py            # data/audio → data/audio_orig 退避後、正規化版を data/audio に生成
  python3 normalize_audio.py --check    # 正規化済みかの検査のみ
"""
import argparse
import os
import shutil
import sys

import numpy as np
import soundfile as sf

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
ORIG_DIR = os.path.join(DATA_DIR, "audio_orig")

TARGET_PEAK = 0.5  # -6 dBFS


def normalize_file(src: str, dst: str) -> dict:
    data, sr = sf.read(src)
    peak = float(np.abs(data).max())
    scale = (TARGET_PEAK / peak) if peak > 0 else 1.0
    sf.write(dst, data * scale, sr, format="WAV", subtype="PCM_16")
    return {"peak_before": peak, "scale": scale}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        bad = 0
        for lang in sorted(os.listdir(AUDIO_DIR)):
            d = os.path.join(AUDIO_DIR, lang)
            if not os.path.isdir(d):
                continue
            for f in sorted(os.listdir(d)):
                if not f.endswith(".wav"):
                    continue
                info = sf.info(os.path.join(d, f))
                data, _ = sf.read(os.path.join(d, f))
                peak = float(np.abs(data).max())
                if info.subtype != "PCM_16" or not (0.45 <= peak <= 0.55):
                    print(f"NG {lang}/{f}: subtype={info.subtype} peak={peak:.4f}")
                    bad += 1
        print("check:", "OK (all normalized)" if bad == 0 else f"{bad} files not normalized")
        sys.exit(1 if bad else 0)

    if os.path.exists(ORIG_DIR):
        print(f"{ORIG_DIR} が既に存在 = 正規化済みの可能性。--check で確認を", file=sys.stderr)
        sys.exit(1)

    shutil.move(AUDIO_DIR, ORIG_DIR)
    os.makedirs(AUDIO_DIR)
    n = 0
    for lang in sorted(os.listdir(ORIG_DIR)):
        src_d = os.path.join(ORIG_DIR, lang)
        if not os.path.isdir(src_d):
            continue
        dst_d = os.path.join(AUDIO_DIR, lang)
        os.makedirs(dst_d, exist_ok=True)
        for f in sorted(os.listdir(src_d)):
            if not f.endswith(".wav"):
                continue
            meta = normalize_file(os.path.join(src_d, f), os.path.join(dst_d, f))
            n += 1
            if meta["scale"] > 10:
                print(f"  {lang}/{f}: 大幅増幅 x{meta['scale']:.1f} (元peak={meta['peak_before']:.4f})")
    print(f"normalized {n} files → {AUDIO_DIR} (originals in {ORIG_DIR})")


if __name__ == "__main__":
    main()
