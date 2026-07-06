---
license: cc-by-4.0
task_categories:
- automatic-speech-recognition
language:
- de
- en
- es
- fr
- id
- ja
- ko
- pt
- ru
- th
- vi
- zh
tags:
- benchmark
- speech-to-text
- asr-evaluation
- fleurs
- stt
pretty_name: koedesk STT Bench — 13 engines × 12 languages, raw transcriptions
size_categories:
- 10K<n<100K
configs:
- config_name: transcriptions
  data_files: data/transcriptions.parquet
  default: true
- config_name: cell_scores
  data_files: data/cell_scores.parquet
---

# koedesk STT Bench — raw transcriptions (v1, Track A)

**28,400 raw transcriptions**: 13 hosted speech-to-text engine variants × 12 languages × 200 FLEURS utterances, produced by a **preregistered** benchmark run on 2026-07-05. Every engine output is published unmodified, including full raw API responses.

**Conflict of interest, stated first**: this benchmark is built and funded by [koedesk](https://koedesk.app), a voice-typing product that uses ElevenLabs Scribe v2. We do not pretend to be neutral. Instead, everything you need to distrust us and re-score the data yourself is public: the methodology was frozen in [`PREREGISTRATION.md`](https://github.com/guide-inc-org/koedesk-stt-bench/blob/main/PREREGISTRATION.md) *before* the headline run (verifiable from git history), all raw outputs are in this dataset, and the scoring code is MIT-licensed on GitHub. Where Scribe loses, the result is published unchanged — it is not #1 overall.

- **Leaderboard**: https://koedesk.app/benchmark/
- **Methodology, scoring code, normalizers, amendments**: https://github.com/guide-inc-org/koedesk-stt-bench
- **Write-ups**: [English](https://koedesk.app/blog/stt-benchmark/) · [日本語 (Zenn)](https://zenn.dev/koedesk/articles/stt-benchmark-13-engines-12-languages)

## Configs

### `transcriptions` (28,400 rows)

One row per (engine variant, language, utterance).

| column | type | description |
|---|---|---|
| `engine` | string | Engine variant key (matches `scores.json` / leaderboard) |
| `model_id` | string | Exact model identifier sent to the API |
| `lang` | string | Benchmark language code (see FLEURS mapping below) |
| `utt_id` | string | `{lang}_{index:04d}` — index into the FLEURS test split, dataset order |
| `duration_sec` | float | Audio duration |
| `ref_text_raw` | string | FLEURS reference transcription, untouched |
| `ref_text_normalized` | string | Reference after the preregistered normalization pipeline |
| `hypothesis` | string | Engine output text, untouched |
| `latency_sec` | float | Wall-clock API latency for this utterance |
| `timestamp_utc` | string | When the API call was made |
| `retries` | int | Retry count for this utterance |
| `error` | string/null | Final error, if any (all rows in v1 completed successfully) |
| `params_json` | string | JSON: exact request parameters |
| `raw_response_json` | string | JSON: the **full, untruncated** API response |

### `cell_scores` (142 rows)

One row per (engine, language) cell, computed by the frozen scoring code ([`make_scores.py`](https://github.com/guide-inc-org/koedesk-stt-bench/blob/main/make_scores.py)); `scores.json` is also included verbatim at the repo root. Columns include corpus CER/WER, utterance means, bootstrap 95% CIs, real-time-factor percentiles, list price per audio hour, and the tie group (`tie_group`, 1 = best tier). The headline metric is CER for ja/th/zh and WER elsewhere (`headline_metric` column); `wer_*` is null for `th` (no whitespace word boundaries).

**Read results through tie groups, not raw ranks.** Within a tie group, pairwise differences are not statistically distinguishable (paired bootstrap, preregistered in §6). Claiming "engine A beats engine B" inside the same tier is exactly the misuse this benchmark tries to prevent.

## Engines (13 hosted variants)

| engine | model_id | languages |
|---|---|---|
| `elevenlabs` | scribe_v2 | 12 |
| `openai` | gpt-4o-transcribe | 12 |
| `whisper1` | whisper-1 | 12 |
| `google_stt_v2` | chirp_3 | 12 |
| `deepgram` | nova-3 | 12 |
| `mai_transcribe` | mai-transcribe-1.5 | 12 |
| `gemini` | gemini-2.5-flash | 12 |
| `gemini_25_pro` | gemini-2.5-pro | 12 |
| `gemini_31_flash_lite` | gemini-3.1-flash-lite | 12 |
| `gemini_31_pro` | gemini-3.1-pro-preview | 12 |
| `gemini_35_flash` | gemini-flash-latest | 12 |
| `mistral_voxtral` | voxtral-mini-2602 | 9 (no id/th/vi) |
| `amivoice` | -a-general | 1 (ja only) |

Engine selection and exclusions (e.g. engines whose terms of service prohibit publishing benchmark results) are documented in the [ToS audit](https://github.com/guide-inc-org/koedesk-stt-bench/blob/main/tos-audit.md).

## Audio provenance (audio is NOT redistributed here)

Test material is the [google/fleurs](https://huggingface.co/datasets/google/fleurs) **test split, first 200 utterances in dataset order** per language (deterministic — no sampling choices). To reconstruct the exact audio: load the config below, take rows 0–199 of the test split, then apply [`normalize_audio.py`](https://github.com/guide-inc-org/koedesk-stt-bench/blob/main/normalize_audio.py) (16-bit PCM, −6 dBFS peak — the identical file was sent to every engine).

| lang | FLEURS config | lang | FLEURS config |
|---|---|---|---|
| ja | ja_jp | ko | ko_kr |
| en | en_us | vi | vi_vn |
| zh | cmn_hans_cn | id | id_id |
| de | de_de | th | th_th |
| fr | fr_fr | es | es_419 |
| pt | pt_br | ru | ru_ru |

## Known artifacts (kept as measured, per the preregistration)

- **`gemini_25_pro` / `zh` / `zh_0192`**: the model leaked ~4,800 characters of English reasoning into the transcription field for one utterance. That single utterance accounts for 86.7% of the cell's error mass (CER 48.3% as measured; 6.45% excluding it). This is the engine's real behavior, not a pipeline bug, and is published as measured.
- **FLEURS zh references**: 13/200 reference texts contain English annotation notes from the source dataset; this affects all engines identically.
- **Gemini-family latency**: measured through Cloudflare AI Gateway (affects `latency_sec`/RTF for the five `gemini*` variants only; accuracy is unaffected). All other engines were called directly.
- **Measurement environment**: run from Vietnam with an AWS Tokyo exit node (see Amendment 6).

## Limitations

This is **Track A only**: FLEURS is public and every commercial engine has plausibly trained on it. These numbers connect to vendor-claimed figures and the HF Open ASR Leaderboard; they do not prove real-world dictation accuracy. A planned Track B (fresh recorded audio) was cancelled before any measurement existed — see [Amendment 7](https://github.com/guide-inc-org/koedesk-stt-bench/blob/main/AMENDMENTS.md). The benchmark refreshes quarterly (§9 of the preregistration).

## License and attribution

- This dataset (transcriptions, scores, documentation): **CC BY 4.0**, © 2026 Guide Inc. (koedesk).
- Reference texts (`ref_text_raw`, `ref_text_normalized`) derive from **FLEURS** ([google/fleurs](https://huggingface.co/datasets/google/fleurs), CC BY 4.0; Conneau et al., 2022, *FLEURS: Few-shot Learning Evaluation of Universal Representations of Speech*).
- Engine outputs are published for evaluation/research purposes; each provider's terms were audited before inclusion (see ToS audit).

## Citation

```bibtex
@misc{koedesk-stt-bench-2026,
  title  = {koedesk STT Bench: a preregistered multilingual speech-to-text benchmark},
  author = {{Guide Inc. (koedesk)}},
  year   = {2026},
  url    = {https://koedesk.app/benchmark/},
  note   = {Raw data: https://huggingface.co/datasets/koedesk/stt-bench. Methodology: https://github.com/guide-inc-org/koedesk-stt-bench}
}
```
