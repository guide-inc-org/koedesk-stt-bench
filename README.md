# koedesk STT Bench

Multilingual speech-to-text benchmark, built and funded by [koedesk](https://koedesk.app).

**We do not pretend to be neutral** — koedesk uses ElevenLabs Scribe v2. Instead, everything you need to distrust us and re-run the benchmark yourself is published here: the preregistered methodology (committed *before* any headline run — see the commit history of `PREREGISTRATION.md`), all raw engine outputs, all scoring code, and the terms-of-service audit that decided which engines could be included at all. If Scribe loses in a language, that result is published unchanged.

## Documents

| File | What it is |
|------|-----------|
| [`PREREGISTRATION.md`](PREREGISTRATION.md) | The frozen methodology: engines, languages, test material, normalization, scoring, statistics, publication commitments. **Binding since its initial commit.** |
| [`tos-audit.md`](tos-audit.md) | Per-provider terms-of-service audit (in Japanese). Engines whose terms prohibit benchmarking are excluded and the clauses are quoted. |
| [`normalize_audio.py`](normalize_audio.py) | Audio delivery normalization (16-bit PCM, −6 dBFS peak) applied identically to every engine — see PREREGISTRATION §4. |

## Status

- 2026-07-04: Preregistration v1.0 frozen. Pilot (rule-debugging only; numbers never published) completed.
- Headline runs, per-language results, and the leaderboard at `koedesk.app/benchmark/` follow.

## License

Code: MIT. Benchmark documents: CC-BY 4.0. (Track B audio, when recorded, ships under CC-BY 4.0 — see PREREGISTRATION §4.)
