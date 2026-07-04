# Preregistration: Multilingual STT Benchmark (koedesk STT Bench v1)

**Status**: v1.0 — **FROZEN**. This document is binding as of its initial commit to this public repository (2026-07-04). Any later change goes through the versioned amendment process only (see §5 last paragraph and §9): the change, the reason, and results under both old and new rules are published together.
**Preregistration version**: v1.0 (2026-07-04)
**Author / Conflict of interest**: This benchmark is built and funded by koedesk (a dictation product that uses ElevenLabs Scribe v2 as one of its engines). We do not pretend to be neutral — instead, everything needed to distrust us and re-run the benchmark yourself is published: methodology (this document, committed *before* the headline runs), all raw engine outputs, all scoring code, and all fresh audio. If Scribe v2 loses in a language, that result is published unchanged.

---

## 1. What is being measured

Transcription accuracy of major speech-to-text engines, **per language**, on (a) public test sets and (b) freshly recorded 2026 audio that no engine can have trained on. Primary metrics are corpus-level WER and CER with bootstrap confidence intervals. Secondary metrics: technical-term recall, latency, and price.

## 2. Engines (v1)

| # | Engine | Access | Version pinning |
|---|--------|--------|-----------------|
| 1 | ElevenLabs Scribe v2 | API | `model_id` recorded per run |
| 2 | OpenAI gpt-4o-transcribe | API | model string + response `model` field recorded |
| 3 | OpenAI whisper-1 | API | legacy baseline |
| 4 | Google Cloud Speech-to-Text v2 (Chirp family) | API | recognizer/model name recorded |
| 5 | Gemini audio input — family comparison: 2.5 Flash, 2.5 Pro, 3.1 Flash-Lite, 3.1 Pro, 3.5 Flash | API | model string recorded per variant. 3.1 Pro is available only as `-preview` (noted as such). 3.5 Flash is reachable only via the `gemini-flash-latest` alias at pilot time; the alias's resolved model per Google's official changelog is recorded with an as-of date on every run, and a pinned ID replaces the alias as soon as one is provisioned |
| 6 | Deepgram Nova-3 | API | model + API version recorded |
| 7 | AmiVoice API (会話_汎用 `-a-general`) | API | ja only; engine name recorded |
| — | ~~xAI Grok Speech-to-Text~~ | API | **Excluded per R-2.1** (decision 2026-07-04): xAI's Enterprise Customer Agreement prohibited-use clause (j) — "use or permit the use of any tools in order to probe, scan or attempt to penetrate or benchmark any Services" — names benchmarking explicitly; treated under the same standard as AssemblyAI. Re-enters only with written consent. Process note: a pilot cell was run before this audit (an ordering violation of R-2.1 on our side, recorded in §7); its data stays internal and unpublished |

Scope note: the benchmark covers **hosted APIs only** — the products a buyer can actually call. Self-hosted OSS models (Whisper large-v3 local, Parakeet, etc.) are out of scope for v1; the HF Open ASR Leaderboard already covers them, and our en/de/fr/es/pt normalization is pinned to the same Whisper normalizer so results remain methodologically comparable. AssemblyAI is excluded per R-2.1 below.

Rules:

- **R-2.1** Engines whose Terms of Service prohibit publishing benchmark results, or require prior written consent we did not obtain, are excluded before any measurement, and the exclusion + the clause are documented publicly. TOS audit result (2026-07-04, details in `tos-audit.md`):
  - **AssemblyAI: excluded from v1.** Its ToS §2.4(f) prohibits using the service for "competitive analysis or benchmarking" — running the test at all, not just publishing, would breach it. It re-enters only with written consent.
  - **xAI Grok STT: excluded from v1** (audited 2026-07-04, after its pilot cell had already run — see §7 for the process note). Enterprise Customer Agreement prohibited-use (j): "...probe, scan or attempt to penetrate or benchmark any Services". The security-testing framing of the surrounding words arguably narrows it, but the explicit word "benchmark" puts it in the AssemblyAI class under our own standard. Re-enters only with written consent.
  - **Google Cloud STT: included under conditions we meet by design** (GCP Service Specific Terms §7: full reproducibility disclosure — which this whole project is — and accepting that Google may reciprocally benchmark our public product; accepted).
  - **Gemini API: treated under the same GCP conditions** (its own terms have no benchmark clause; whether GCP terms extend to it is unresolved, so we conservatively assume they do).
  - **Azure (v2 candidate): conditional** (Microsoft "Competitive Benchmarking" clause: on request we must provide reproduction info — already public by design — and cooperate with counter-benchmarks).
  - ElevenLabs, OpenAI, Whisper (MIT), Deepgram, AmiVoice, Speechmatics: no benchmark-restricting clause found.
- **R-2.2** Every API call specifies the target language explicitly (matching how a dictation product actually calls these APIs). Auto-detect results, if collected, are reported separately as reference only and are not part of the headline table.
- **R-2.3** No keyword boosting, custom vocabulary, content hints, or biasing features are used for any engine in the headline runs. For LLM-type engines (Gemini), which cannot be invoked without an instruction, a single fixed minimal transcription instruction is used — identical across all languages except the language name, published verbatim in the engine adapter, and containing no vocabulary or domain hints ("Transcribe this audio verbatim in its original language ({lang}). Output only the transcription, nothing else."). The instruction is the invocation mechanism, not a biasing feature. (A separate future track may test vendor dictionary features; it will be labeled as such.)
- **R-2.4** Default punctuation/formatting settings of each API are used; diarization off; single channel.
- **R-2.5** The full request parameters and full raw API responses are committed for every utterance.
- **R-2.6** An engine's run for a language happens within one contiguous window (≤72h) and the run date is recorded. APIs are moving targets; the leaderboard shows "as of" dates per engine.

## 3. Languages (v1: 12)

ja, en, zh (Mandarin, simplified), ko, vi, id, th, de, fr, es, pt, ru.

Headline metric per language: **CER for ja, zh, th; WER for all others. Both are always computed and displayed for every language.**

Declared before measurement: per ElevenLabs' own published language tiers (docs, retrieved 2026-07-04), 9 of these 12 are in Scribe's "Excellent" tier (ja, en, vi, id, de, fr, es, pt, ru), zh is "High", and ko/th are "Good". The language set was **not** trimmed to Scribe's strongest tier; ko and th are included knowing Scribe may lose there, consistent with §9.

## 4. Test material

**Audio delivery normalization (rule added at pilot, 2026-07-04).** Every utterance, from any track, is delivered to every engine as the same preprocessed file: 16-bit PCM WAV, peak-normalized to -6 dBFS (deterministic per-file scale factor; silence unchanged; sample rate and channel count unchanged; code published as `normalize_audio.py`). Rationale, found in pilot batch 3: FLEURS contains utterances mastered as low as -44 dBFS peak; one engine (Grok STT) silently returns empty text for such input while every other engine transcribes it, and another (AmiVoice) rejects float32 WAV outright. Unnormalized levels therefore measure a dataset mastering artifact rather than transcription accuracy (real dictation input passes through microphone AGC). The identical normalized file goes to every engine — engine-specific preprocessing remains prohibited — and the quiet-audio robustness behavior itself is reported as an auxiliary finding outside the headline table.

### Track A — public test sets (comparability)

- **FLEURS** test split, per language: the **first 200 utterances in dataset order** (deterministic; no sampling choice for us to fiddle).
- **Common Voice** (newest release available at run time; version recorded) test split: first 200 validated utterances in dataset order.
- Known caveat, stated up front: every commercial engine has plausibly trained on these sets. Track A exists to connect to vendor-claimed numbers and to the HF Open ASR Leaderboard, not to prove real-world accuracy.

### Track B — fresh 2026 audio (contamination-proof; the point of this benchmark)

Per language, target ≈30 minutes, three categories:

| Cat | Material | Purpose |
|-----|----------|---------|
| B-1 | New scripts written in 2026 (news-register + everyday-register), read by native speakers | controlled comparison |
| B-2 | Impromptu speech on a given topic (fillers, restarts included) | closest to real dictation |
| B-3 | Scripts dense with technical terms / product names / proper nouns | the dictation-for-work use case |

- Scripts are authored (not machine-translated verbatim) per language; native speakers may naturalize phrasing before recording, and the **recorded reading is re-transcribed by a human to produce the reference** (the reference is what was actually said, not what the script said).
- **No TTS audio anywhere.** Synthetic speech is not a valid measurement of STT and would double-bias any same-vendor pair.
- Recording spec: 44.1 kHz / 16-bit WAV; quiet room; a noisy-condition track (cafe-level SNR, produced by mixing recorded noise at a documented SNR) is a labeled separate condition, not blended into headline numbers.
- All Track B audio + references released under **CC-BY 4.0**.
- Languages whose Track B recordings are not ready at v1 publication ship with Track A only, marked "fresh audio pending" — predeclared here so shipping partial Track B is not a post-hoc choice.
- **v1 scope decision (2026-07-04, pre-freeze)**: no speaker recruitment is funded for v1 — **all 12 languages ship Track A only at v1**, every language marked "fresh audio pending". This section remains the binding design for Track B if and when recordings are made; the contamination caveat of Track A (§4 Track A) is stated prominently in the v1 article.

## 5. Normalization (frozen at preregistration; code + tests published)

Normalization is where STT benchmarks are silently rigged, so the entire pipeline is pinned here and in code. The same pipeline is applied to reference and hypothesis. Order:

1. **Unicode NFKC** normalization.
2. **Case folding** for cased scripts (Latin, Cyrillic).
3. **Punctuation & symbol removal**: all Unicode categories `P*` and `S*`, with one exception: word-internal apostrophes in Latin-script languages are kept (English contractions: `don't`), then standardized `’`→`'`.
4. **Whitespace**: collapse runs to single space; strip.
5. **Number equivalence** (the single most contested area — the full mapping table ships as code; classes below were validated against 378 real pilot transcripts):
   - Spelled-out cardinals **and ordinals** are converted to digits per language by a deterministic, published converter (en: `twenty-one`→`21`, `twentieth`→`20th`→`20`; ja: 漢数字→arabic digits for integers 0–99,999, including positional mixed forms `三万三千`/`3万3000`→`33000` and ordinal `第二十`→`第20`). Observed in pilot: `78`⇔`七十八`, `twentieth century`⇔`20th century`.
   - **Digit-group separators are removed inside number tokens** per a published per-language convention table (en/ja: `33,000`→`33000`; languages where `.` groups thousands and `,` marks decimals, e.g. de/es/pt, use their own row of the table). Observed in pilot: `33,000`⇔`33000`.
   - Numeric ranges: hyphens between digits become token boundaries via punctuation removal (`25-30`→`25 30`), while spelled connectors (`to`, `から`) remain tokens. The residual one-token asymmetry is a declared, known measurement noise — no special-case rule (adding one would create a new arbitrary surface).
   - Where conversion is ambiguous (ja counters like 一人/ひとり, idiomatic uses, dates), the case classes and their handling are enumerated in `normalizers/<lang>/numbers_test.py`; ambiguous classes are left untouched (both sides), never resolved case-by-case by a human looking at results.
6. **Language-specific rules** (each with its own test file):
   - **ja**: NFKC handles full/half width; unify 長音記号 variants (U+30FC vs hyphen-like lookalikes); **no kana⇄kanji or katakana⇄hiragana unification in v1** — this is declared a known limitation, mitigated by CER being the headline (partial credit at character level). WER tokenizer: MeCab + UniDic (version pinned in lockfile).
   - **zh**: text is scored as given (simplified); if an engine emits traditional, OpenCC t2s conversion is applied (declared, code committed). WER tokenizer: jieba (pinned). Headline: CER.
   - **th**: no word segmentation; CER only (WER column shows "—").
   - **en / de / fr / es / pt**: on top of steps 1–5, the pinned **Whisper open-source normalizer** (English normalizer for en; Basic for others) is applied so that our en/de/fr/es/pt numbers are methodologically comparable with the HF Open ASR Leaderboard; its version/commit is pinned. Built-in sanity check: our Track A numbers are cross-checked against vendor-published FLEURS claims (e.g., ElevenLabs' own Scribe figures) — a large unexplained divergence means we investigate our pipeline before publishing, and any remaining divergence is reported rather than hidden.
   - **ko / vi / id / ru**: steps 1–5 plus whitespace-delimited WER; any additional rule ships in code with tests before the headline run.
7. **Fillers** (applies to Track B-2 only): a per-language filler lexicon is published in `normalizers/<lang>/fillers.txt` (e.g. ja: えー, えーと, あのー, まあ, うーん…; en: uh, um, you know (as discourse filler)…). B-2 is scored **two ways**: *verbatim* (fillers count) and *filler-tolerant* (filler tokens deleted from both reference and hypothesis before scoring). Both are published; the B-2 headline is filler-tolerant (a dictation product that drops "um" is not making an error). B-1/B-3 and Track A are verbatim only.

Any normalization change after the preregistration commit requires a versioned amendment: the change, the reason, and headline tables under **both** the old and new rules are published together.

## 6. Scoring & statistics (frozen)

- **Alignment**: token-level (WER) / character-level (CER) Levenshtein alignment, uniform costs (S=D=I=1). Implementation committed with unit tests including tricky cases.
- **Aggregation**: corpus-level rate = Σ(edit errors) / Σ(reference length) over all utterances of a (language, track, engine) cell. Utterance-level mean is also reported but is not the headline.
- **Confidence intervals**: nonparametric bootstrap resampling utterances with replacement, **n = 10,000, seed = 20260704**, percentile method (2.5/97.5). Shown on every headline number.
- **Pairwise comparison**: engines are compared with **paired** bootstrap on the same utterance set; two engines are "statistically distinguishable" iff the 95% CI of their paired difference excludes 0. The leaderboard displays rank *groups*: engines not distinguishable from the group leader share the tier. We never claim a win inside a tie group — including for Scribe v2.
- **Empty output**: an engine returning empty text for an utterance scores all-deletions. It is **never** excluded — excluding empties is the classic way to launder a bad engine.
- **Hard failures**: an API error persisting after 3 retries (exponential backoff, then one final retry in a later window) causes that utterance to be dropped **for all engines in that language** (keeps the design paired), and is listed in an errata file. If >2% of a language's utterances are dropped this way, the language's results are flagged as degraded.
- **Secondary metrics**:
  - *Technical-term recall* (B-3 only): per-term recall against a published term list per script; a term counts as recalled if its normalized form appears in the normalized hypothesis.
  - *Latency*: wall-clock seconds per audio second (RTF), request-to-response, measured from one machine/network (Mac mini, Tokyo-region ISP), reported as median (p50) and p90. Informational, not a ranking axis.
  - *Price*: vendor list price per audio-hour at run date.
- **Semantic-preservation score (auxiliary, B-2 only)**: an LLM-judge rates whether hypothesis preserves the meaning of the reference (fabrications/omissions), prompt + judge model pinned and published, 3 independent votes, median taken. Reported in the article as an auxiliary view, never in the leaderboard ranking.

## 7. Pilot declaration

Before this preregistration is finalized, a pilot is run to debug the pipeline and stress the normalization rules against real outputs. The pilot is declared here explicitly, in two batches (both ja/en × FLEURS first-100, run 2026-07-04):

- **Batch 1** — 3 engines (Scribe v2, gpt-4o-transcribe, local Whisper large-v3; the local model serves rule-stressing only and is out of v1 headline scope per §2).
- **Batch 2** — the Gemini family (2.5 Flash, 2.5 Pro, 3.1 Flash-Lite, 3.1 Pro preview, 3.5 Flash via `gemini-flash-latest`), added the same day to pin the LLM-type engine list and validate the fixed-instruction invocation (R-2.3) against real audio. Total pilot corpus: 8 engine variants × 2 languages × 100 utterances = 1,600 transcripts, zero API errors, zero empty transcripts.
- Pilot data is used to *fix the rules*, and pilot numbers are never published as results. (Audit outcome, 2026-07-04, batch 1's 378 transcripts: added three number-equivalence classes — ordinals, digit-group separators, ja positional mixed forms — and confirmed punctuation stripping is required for cross-engine fairness: one engine emitted ja punctuation in 100/100 utterances, another omitted it in 62/100. No empty transcripts, language contamination, or length-ratio outliers were observed. Batch 2 additionally surfaced token-spaced ja output from 3.1 Flash-Lite — handled by the whitespace rule §5.4 — and is subject to the same audit before freeze.)
- **Batch 3** (same day, evening) — AmiVoice 会話_汎用 (ja×100) and xAI Grok STT (ja/en×100 each), added after the engine-list decision. **Process violation, recorded**: the Grok cell was run *before* its TOS audit, breaching R-2.1's audit-then-measure ordering (AmiVoice had been audited in advance). The audit then found the ECA (j) benchmark clause → Grok STT is excluded (§2); all its pilot data stays internal and no Grok number is ever published. The ordering rule is restated: no new engine is called before its TOS audit is on file. Two rule-relevant findings from this batch, both fixed pre-freeze:
  - AmiVoice rejects float32 WAV ("unsupported audio format") — FLEURS-derived files were float32.
  - Grok STT silently returns empty text (HTTP 200, zero words) for very quiet input: 61/100 en and 12/100 ja utterances, all with peak ≈ -44 dBFS; amplifying the identical audio to -6 dBFS yields a full transcription, and all nine other engine variants transcribe the quiet originals. → Both findings motivated the §4 audio delivery normalization rule (16-bit PCM, -6 dBFS peak, identical for all engines). The Grok cells were re-run on normalized audio; batches 1–2 cells were not re-run (pilot data is not results; headline runs use normalized delivery for every engine from scratch).
- A known pilot-vs-rules gap is recorded for transparency: batch runs before 2026-07-04 evening stored truncated raw API responses (R-2.5 requires full responses). The adapters were fixed the same day; headline runs store full raw responses. Pilot artifacts are kept as-is (they are not results).
- The headline runs re-run those cells from scratch on the full preregistered sets.
- Nothing in §5/§6 may be changed after preregistration based on how it affects any engine's ranking; post-freeze changes go through the amendment process only for defects (e.g., a normalizer bug), not for outcomes.

## 8. Reproduction

`make bench LANG=<lang> ENGINE=<engine|all> TRACK=<a|b>` re-runs any cell with your own API keys. The repo contains: this document, all normalizer/scoring code with tests, dataset fetch scripts (public sets), all Track B audio (CC-BY), every raw API response, and the scores table generator. The published leaderboard is generated from `results/scores.json` by CI — no hand-edited numbers.

## 9. Publication commitments

- All 12 languages' results are published, including every language where Scribe v2 loses.
- Track A vs Track B divergence is reported prominently (it is the headline question of the accompanying article).
- The leaderboard states per-engine run dates and the next scheduled refresh (quarterly).
- Errata and amendments are append-only and dated.
