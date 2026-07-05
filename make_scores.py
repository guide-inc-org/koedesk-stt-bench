#!/usr/bin/env python3
"""
scores.json ジェネレータ (PREREGISTRATION §6 / §8 "the scores table generator")。

results/raw/{engine}/{track}/{lang}/{utt_id}.json を読み、凍結済みの
normalizers/ + scoring/ だけを使って results/scores.json を生成する。
手編集ゼロ (§8)。決定論的出力: 同じ raw に対して 2 回実行して diff ゼロ。

使い方:
    python3 make_scores.py                 # results/raw 全量 → results/scores.json
    python3 make_scores.py --track a
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from normalizers.de import normalize_de, tokenize_de
from normalizers.en import normalize_en, tokenize_en
from normalizers.es import normalize_es, tokenize_es
from normalizers.fr import normalize_fr, tokenize_fr
from normalizers.id_ import normalize_id, tokenize_id
from normalizers.ja import normalize_ja, tokenize_ja
from normalizers.ko import normalize_ko, tokenize_ko
from normalizers.pt import normalize_pt, tokenize_pt
from normalizers.ru import normalize_ru, tokenize_ru
from normalizers.th import normalize_th
from normalizers.vi import normalize_vi, tokenize_vi
from normalizers.zh import normalize_zh, tokenize_zh
from scoring.bootstrap import bootstrap_ci, tie_groups
from scoring.metrics import corpus_rate, utterance_errors, utterance_mean_rate

ROOT = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(ROOT, "results", "raw")
OUT = os.path.join(ROOT, "results", "scores.json")

# §3: headline metric per language — CER for ja/zh/th, WER for all others.
CER_HEADLINE = {"ja", "zh", "th"}

NORMALIZE = {
    "ja": normalize_ja, "zh": normalize_zh, "th": normalize_th,
    "en": normalize_en, "de": normalize_de, "fr": normalize_fr,
    "es": normalize_es, "pt": normalize_pt, "ru": normalize_ru,
    "ko": normalize_ko, "vi": normalize_vi, "id": normalize_id,
}
TOKENIZE = {
    "ja": tokenize_ja, "zh": tokenize_zh,
    "en": tokenize_en, "de": tokenize_de, "fr": tokenize_fr,
    "es": tokenize_es, "pt": tokenize_pt, "ru": tokenize_ru,
    "ko": tokenize_ko, "vi": tokenize_vi, "id": tokenize_id,
    # th: no word segmentation; WER column shows "—" (§5.6)
}

# §6 secondary metric: vendor list price per audio-hour at run date (informational).
# null = per-hour list price not applicable/published (token-priced or free tier).
PRICE_PER_AUDIO_HOUR_USD = {
    "elevenlabs": 0.22,        # elevenlabs.io/pricing/api batch, no add-ons (R-2.3/R-2.4)
    "openai": 0.36,            # gpt-4o-transcribe ~$0.006/min
    "whisper1": 0.36,          # whisper-1 $0.006/min
    "google_stt_v2": 0.96,     # $0.016/min (0-500K min/mo tier)
    "deepgram": 0.258,         # nova-3 pre-recorded $0.0043/min PAYG
    "mai_transcribe": 0.36,    # Azure Fast Transcription SKU $0.36/h
    "mistral_voxtral": 0.18,   # Voxtral Mini Transcribe V2 $0.003/min
    "amivoice": None,          # measured on free tier; paid list price is per-engine JPY
    "gemini": None,            # token-priced via CF AI Gateway; no per-hour list price
    "gemini_25_pro": None,
    "gemini_31_flash_lite": None,
    "gemini_31_pro": None,
    "gemini_35_flash": None,
}


def cer_normalize(lang: str, text: str) -> str:
    fn = NORMALIZE[lang]
    if lang in ("ja", "zh", "th"):
        return fn(text, strip_all_whitespace_for_cer=True)
    return fn(text)


def load_cell(engine: str, track: str, lang: str) -> list[dict]:
    d = os.path.join(RAW, engine, track, lang)
    recs = []
    for fname in sorted(os.listdir(d)):
        if fname.endswith(".json"):
            with open(os.path.join(d, fname), encoding="utf-8") as f:
                recs.append(json.load(f))
    return recs


def score_cell(lang: str, recs: list[dict]) -> dict:
    """1セル (engine, track, lang) の per-utterance 誤りと補助指標を計算。"""
    per_utt_cer, per_utt_wer, rtfs = [], [], []
    empty = 0
    model_ids = set()
    run_dates = set()
    for r in recs:
        ref_raw = r["ref_text_raw"]
        hyp = (r.get("text") or "")
        if not hyp.strip():
            empty += 1  # §6: all-deletions として必ず採点（除外禁止）

        # CER
        ref_c = cer_normalize(lang, ref_raw)
        hyp_c = cer_normalize(lang, hyp)
        u = utterance_errors(ref_c, hyp_c)
        u["utt_id"] = r["utt_id"]
        per_utt_cer.append(u)

        # WER (th は対象外 §5.6)
        if lang in TOKENIZE:
            norm = NORMALIZE[lang]
            ref_w = TOKENIZE[lang](norm(ref_raw))
            hyp_w = TOKENIZE[lang](norm(hyp))
            w = utterance_errors(ref_w, hyp_w)
            w["utt_id"] = r["utt_id"]
            per_utt_wer.append(w)

        if r.get("duration_sec"):
            rtfs.append(r.get("latency_sec", 0.0) / r["duration_sec"])
        params = r.get("params") or {}
        for key in ("model", "model_id", "modelId", "grammarFileNames"):
            if params.get(key):
                model_ids.add(str(params[key]))
        ts = r.get("timestamp_utc") or ""
        if ts:
            run_dates.add(ts[:10])

    def block(per_utt):
        if not per_utt:
            return None
        lo, hi = bootstrap_ci(per_utt)
        return {
            "corpus_rate": round(corpus_rate(per_utt), 6),
            "ci95": [round(lo, 6), round(hi, 6)],
            "utterance_mean": round(utterance_mean_rate(per_utt), 6),
        }

    return {
        "n_utterances": len(recs),
        "empty_transcripts": empty,
        "cer": block(per_utt_cer),
        "wer": block(per_utt_wer),
        "rtf_p50": round(float(np.percentile(rtfs, 50)), 4) if rtfs else None,
        "rtf_p90": round(float(np.percentile(rtfs, 90)), 4) if rtfs else None,
        "model_ids": sorted(model_ids),
        "run_dates": sorted(run_dates),
        "_per_utt_cer": per_utt_cer,
        "_per_utt_wer": per_utt_wer,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--track", default=None, help="a|b (省略時は存在する全トラック)")
    args = ap.parse_args()

    engines = sorted(e for e in os.listdir(RAW) if os.path.isdir(os.path.join(RAW, e)))
    out = {"tracks": {}}
    for engine in engines:
        for track in sorted(os.listdir(os.path.join(RAW, engine))):
            if args.track and track != args.track:
                continue
            for lang in sorted(os.listdir(os.path.join(RAW, engine, track))):
                out["tracks"].setdefault(track, {}).setdefault(lang, {"engines": {}})

    for track, langs in out["tracks"].items():
        for lang, node in langs.items():
            cells = {}
            for engine in engines:
                d = os.path.join(RAW, engine, track, lang)
                if not os.path.isdir(d):
                    continue
                cells[engine] = score_cell(lang, load_cell(engine, track, lang))

            # 発話集合の整合性 (paired 比較の前提)
            utt_sets = {e: {u["utt_id"] for u in c["_per_utt_cer"]} for e, c in cells.items()}
            base = None
            for e, s in utt_sets.items():
                if base is None:
                    base = s
                elif s != base:
                    raise SystemExit(
                        f"utterance set mismatch: {track}/{lang}/{e} — paired design broken"
                    )

            headline = "cer" if lang in CER_HEADLINE else "wer"
            per_utt_key = f"_per_utt_{headline}"
            groups = tie_groups({e: c[per_utt_key] for e, c in cells.items()})

            for e, c in cells.items():
                c.pop("_per_utt_cer")
                c.pop("_per_utt_wer")
                c["price_per_audio_hour_usd"] = PRICE_PER_AUDIO_HOUR_USD.get(e)
                node["engines"][e] = c
            node["headline_metric"] = headline
            node["tie_groups"] = groups

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(f"wrote {OUT}", file=sys.stderr)

    # 人間向けサマリ (stderr)
    for track, langs in sorted(out["tracks"].items()):
        for lang, node in sorted(langs.items()):
            hm = node["headline_metric"]
            parts = []
            for tier_i, tier in enumerate(node["tie_groups"], 1):
                names = ",".join(
                    f"{e}={node['engines'][e][hm]['corpus_rate']:.4f}" for e in tier
                )
                parts.append(f"T{tier_i}[{names}]")
            print(f"{track}/{lang} ({hm.upper()}): " + " ".join(parts), file=sys.stderr)


if __name__ == "__main__":
    main()
