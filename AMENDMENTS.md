# Amendments

Append-only, dated (PREREGISTRATION §9). Each amendment states the change, the reason, and carries the §5 obligation: headline tables are published under the amended rule **and** the pre-amendment rule side by side for every affected cell.

---

## Amendment 1 — §5.4 whitespace handling for unspaced scripts (2026-07-05)

**Change.** For languages whose reference orthography does not use inter-word whitespace (ja, zh, th), **all whitespace is removed** from both reference and hypothesis before CER computation. For spaced languages §5.4 stands as frozen (collapse runs to a single space; strip). WER is unaffected (tokenizers are whitespace-independent by construction).

**Reason — a spec defect found by the declared pilot (§7), not an outcome preference.** §5.4 as frozen says only "collapse runs to single space; strip", so inter-token spaces surviving in a hypothesis count as CER insertions against space-free references. The pilot showed this lets a *formatting* habit dominate a *transcription accuracy* metric: one engine (Gemini 3.1 Flash-Lite) emits token-spaced Japanese under the neutral fixed instruction required by R-2.3, and under the literal reading its pilot ja CER was inflated roughly eightfold by whitespace insertions alone (≈ +33 points), while every other engine moved by only 1–5 points from the same rule choice. A character-error metric in which spaces outweigh actual character errors does not measure what §1 declares is being measured.

**What this amendment does *not* do.** It does not absolve the behavior. Token-spaced CJK output is a real usability defect for dictation — such output requires post-processing before it can be inserted into Japanese text. This is recorded as a **standing auxiliary finding** (same class as the quiet-audio robustness finding in §4/§7): the engines that emit token-spaced Japanese are named in the results publication, with examples, outside the headline table. The dual-table obligation above additionally keeps the literal-rule numbers permanently visible.

**Scope note.** ko keeps §5.4 as frozen (Korean orthography uses inter-word spacing; spacing differences there are genuine orthographic choices, handled by WER/CER as-is).

---

## Amendment 2 — engine addition: MAI-Transcribe-1.5 (2026-07-05)

**Change.** Microsoft **MAI-Transcribe-1.5** (Microsoft first-party STT, GA announced 2026-06-02, accessed via the Azure Speech LLM Speech API) is added to the §2 engine list as engine #8. Version pinning: model name (`mai-transcribe-1.5`) + `api-version` recorded per run, per the §2 convention.

**Reason.** The model was released *after* this plan was drafted and *is the class of claim this benchmark exists to test*: Microsoft claims best-in-class WER across 43 languages and publishes a named speed comparison against ElevenLabs Scribe — a vendor-self-reported claim with no independent per-language verification. Adding it **before any headline measurement has been run** is consistent with the purpose of the engine-list freeze: the freeze exists to prevent outcome-driven inclusion/exclusion, and no headline outcome exists yet for any cell (only the declared §7 pilot, which did not include this engine and whose numbers are never published). Excluding a major new engine for the lifetime of v1 because it shipped weeks after drafting would make the benchmark stale on arrival.

**TOS audit (R-2.1 ordering respected).** Audited 2026-07-05, *before any API call to the engine* — see `tos-audit.md` §2.11. Verdict: conditional, identical to Azure (§2.9): the Microsoft Product Terms "Competitive Benchmarking" clause imposes reciprocity only (provide replication info on request — satisfied by this repo's design — and accept counter-benchmarks); no prohibition, no prior-consent requirement, no xAI-clause-(j)-type language. No MAI-specific additional terms exist (first-party "Models sold directly by Azure" → Microsoft Product Terms apply).

**Declared conditions.**
1. The serving API is in **public preview** at the time of this amendment; every published MAI number is annotated as measured via the preview API.
2. Languages among our 12 that are not in MAI's supported 43 are shown as "not supported" for this engine, not scored. (Checked against the model's Learn documentation on 2026-07-05: **all 12 of our languages are in the supported list**, so this clause is currently vacuous; it stands in case the supported list changes before the run.)
3. No scoring or normalization rule changes accompany this amendment, so the dual-table obligation is not triggered; no existing cell is affected (no headline cell has been measured yet).
4. **`transcribeStyle` declared before measurement.** MAI-Transcribe-1.5 documents that its default output is *readability-optimized* and offers an explicit `transcribeStyle: "verbatim"` mode that "preserves the original spoken content, including filler words and disfluencies". R-2.4 (default settings) was written to prevent per-engine tuning of recognition behavior, not to force scoring a documented rewriting layer against verbatim references: §1 declares that *transcription accuracy* is being measured, and our references are verbatim. Therefore the headline MAI runs use **`transcribeStyle: "verbatim"`**, declared here before any measurement; the default (readability) mode may additionally be reported as a labeled auxiliary view, never as the headline. `phraseList` (entity biasing) is never used, per R-2.3. Locale is always forced via `locales` per R-2.2.

---

## Amendment 3 — normalizer defect fixes from the pre-run adversarial verification pass (2026-07-05)

Before any headline measurement, the normalizers for all 12 languages were subjected to an independent adversarial verification pass (fresh reviewers, real FLEURS reference text swept in bulk, ~500 adversarial probes). Three classes of defect found in the **already-published** `ja` normalizer are fixed here; the same fixes ship in the first publication of `zh`/`th`/`ko`, which are not amendments (per §5.6, language rules ship in code with tests before the headline run). Per §7, post-freeze normalizer changes are allowed for defects only — each item below is a conformance defect against rules already declared, not an outcome preference; no headline cell has been measured under either behavior, so the dual-table obligation is vacuous (declared for completeness).

**Fix 1 — whitespace removal order under Amendment 1 (ja, zh, th).** Amendment 1 declares that for unspaced scripts all whitespace is removed "before CER computation". The implementation removed it *after* number equivalence (§5.5), so a token-spaced hypothesis such as `两千 零 二十 六` fragmented into per-token conversions (`20000206`) instead of converging to `2026`, and blocklist protections for ambiguous classes were bypassed (`万 一 下 雨` → `100001下雨`). This defeats Amendment 1's stated purpose for exactly the engines it addressed. All-whitespace removal now applies before number equivalence in the CER (strip) mode. The literal (frozen §5.4) mode is byte-for-byte unchanged.

**Fix 2 — bare scale-character runs (ja; zh shipped with the guard).** A scale character with no coefficient (`万`, `千`, `百`, `十` standing alone) was converted to its unit value, so the reference orthography `4 万` (digit + space + scale, present in FLEURS zh and possible in ja) became `410000` in strip mode. Bare scale runs are no longer converted.

**Fix 3 — declared converter range enforced (ja).** §5.5 declares the ja converter covers integers 0–99,999; the implementation had no upper-bound check (`一千万` → `10000000`). Runs whose parsed value exceeds 99,999 are now left untouched in full, matching the declared range and the shipped `zh`/`ko` behavior.

All fixes carry regression tests that fail on the pre-fix implementation; the full suite (12 languages + scoring) passes.

---

## Amendment 4 — th normalizer defect fix from the Track A reference-text audit (2026-07-05)

Before any headline measurement, the full Track A reference corpus (FLEURS, first 200 test-split utterances per language, all 12 languages) was swept through the published normalizers with the numeral-conversion stage diffed on/off, and every firing was reviewed by eye. One defect was found; it is fixed here under §7's defects-only rule. No headline cell has been measured under either behavior, so the dual-table obligation is vacuous (declared for completeness).

**Fix — th lexicalized blocklist entry `โกหก`.** The common verb **โกหก** ("to lie") ends in the numeral spelling **หก** (six) and was not in `_LEXICALIZED_BLOCKLIST`, so it was corrupted to `โก6` — the same word-final-numeral-spelling class the blocklist already covers (`เรียบร้อย`, `กองพัน`, …), observed in 2 of the 200 FLEURS th references (th_0018, th_0128). The word is added to the blocklist with regression tests that fail on the pre-fix implementation; the full suite passes. Because both reference and hypothesis pass through the same deterministic normalizer, the pre-fix behavior was symmetric and did not bias any comparison; this is a conformance fix against the §5.5 conservative-conversion rule, not an outcome adjustment.

**Observed and intentionally retained — Unicode vulgar fractions under NFKC (pt).** The same audit surfaced one cosmetic corner of the declared pipeline: NFKC (step 1 of the Latin-script normalizers) decomposes `29¾` to `29` + `3⁄4`, and fraction-slash removal then yields `293 4` (pt_0028; 1 of 200 pt references). This is a direct consequence of the declared NFKC step, is deterministic and symmetric across reference and hypothesis, and no engine output format is advantaged; it is recorded here for transparency and left unchanged. If a future amendment changes fraction handling, this entry marks that the behavior was known before any measurement.

---

## Amendment 5 — engine addition: Mistral Voxtral Mini Transcribe V2 (2026-07-05)

**Change.** Mistral **Voxtral Mini Transcribe V2** (hosted batch transcription API) is added to the §2 engine list as engine #9. Version pinning: the **dated model ID `voxtral-mini-2602`** is used for every call — not the `voxtral-mini-latest` alias, which the `/v1/models` listing resolves ambiguously (it appears aliased to both `voxtral-mini-2507` and `voxtral-mini-2602`; the transcription endpoint resolves it to 2602, confirmed by response `model` field on 2026-07-05).

**Reason.** Voxtral Mini Transcribe V2 is a current-generation, named-comparison claimant against this benchmark's engines: Mistral publishes ~4% average FLEURS WER and claims parity with ElevenLabs Scribe v2 at one-fifth the price, plus wins over GPT-4o mini Transcribe, Gemini 2.5 Flash and Deepgram Nova — exactly the class of vendor-self-reported claim this benchmark exists to verify independently. Unlike MAI (Amendment 2), this model predates the plan's drafting; its absence from the frozen list was a drafting oversight, not an outcome-driven choice. The engine-list freeze exists to prevent outcome-driven inclusion/exclusion, and **no headline cell has been measured for any engine**, so adding it now cannot be outcome-driven. "Mini" is the flagship: Mistral offers no larger dedicated transcription model (the transcription endpoint rejects `voxtral-small-2507`, verified 2026-07-05; that model is the 2025 audio-understanding LLM, not the STT product).

**TOS audit (R-2.1 ordering respected).** Audited 2026-07-05, before any API call — see `tos-audit.md` §2.12. Verdict: publishable; no benchmark-restricting clause in the Commercial Terms of Service (2026-05-28), Usage Policy (2026-06-11), or Additional Product Terms (2026-05-28). After the audit and before this amendment, a connectivity smoke (en/ja, 2 utterances) was run — permitted by the declared adapter-then-amendment-then-headline ordering; no headline measurement has occurred.

**Declared conditions.**
1. **Language coverage 9/12.** The documented supported set (en, zh, hi, es, ar, fr, pt, ru, de, ja, ko, it, nl) excludes **vi, id, th**. Those cells are shown as "not supported" for this engine, not scored (same treatment as AmiVoice outside ja).
2. `context_bias` (vocabulary biasing) is never used, per R-2.3. `diarize` off, timestamps off, defaults otherwise, per R-2.4. Language is always passed explicitly, per R-2.2 (plain ISO-639-1 codes; the API offers no regional variants, so es/pt map to `es`/`pt` and this is recorded in the adapter's mapping table).
3. No scoring or normalization rule changes accompany this amendment; the dual-table obligation is not triggered (no cell measured under any prior rule).
4. Pricing recorded at amendment time: $0.003/min (vendor announcement); to be cross-checked against the billing dashboard after the first run.

---

## Amendment 6 — correction of the §6 latency measurement-environment description (2026-07-05)

**Defect.** §6 described the latency measurement environment as "one machine/network (Mac mini, Tokyo-region ISP)". This is factually wrong in two ways, discovered after the Track A publication when the operator flagged it: the measurement machine (Mac mini) is physically located in **Vietnam**, and its egress is not a Tokyo ISP but a **company VPN exit node on AWS ap-northeast-1 (Tokyo)** (measured RTT from the machine to the exit node ≈ 86 ms at correction time). Every request from every engine cell traversed this identical path.

**Impact on published numbers: none are changed.** Latency (RTF p50/p90) is an informational metric, not a ranking axis (§6). Because the VPN hop is common to all engines, relative RTF comparison is unaffected; absolute RTF values include a fixed per-request overhead from the Vietnam→Tokyo hop and TLS setup over it. `results/scores.json` is untouched by this amendment. Accuracy metrics never depended on the network description.

**Change.** The §6 environment sentence is corrected in place with a reference to this amendment, and the leaderboard page's footer and latency note are corrected to match. This is a defects-only documentation fix under §7; no scoring, normalization, or data change accompanies it.

---

## Amendment 7 — v1 scope: Track A only; Track B cancelled (2026-07-06)

**Change.** The v1 scope of this benchmark is **Track A only**. Track B (fresh 2026 recorded audio, §4) is **cancelled** — not "pending", not deferred. The §9 commitment *"Track A vs Track B divergence is reported prominently"* is withdrawn. The §4 Track B design section remains in the document unedited as the record of what was planned; it is no longer a commitment of this benchmark.

**Reason.** Track B's pipeline is human at every load-bearing step: scripts are authored per language by humans, native speakers naturalize phrasing before recording, and the reference is produced by a human re-transcription of the recording. Each of those steps injects judgment that cannot be frozen in code, cannot be diffed, and cannot be reproduced deterministically by a third party. This benchmark's declared value (§1, §5, §8) is mechanical reproducibility — every published number can be recomputed from published audio, published code, and published raw API responses with zero human decisions in the loop. Track B as designed cannot meet that bar, so it is dropped rather than shipped at a lower evidentiary standard than Track A.

**Not outcome-driven — and why that is verifiable.** No Track B audio was ever recorded and no Track B measurement of any engine was ever run; the repository's full public history contains no Track B artifact of any kind. A scope decision cannot be conditioned on results that do not exist. The §4 v1 scope decision (2026-07-04, pre-freeze) had already shipped v1 with zero Track B recordings; this amendment converts that "fresh audio pending" state into a definitive cancellation.

**What remains.** Track A's known limitation stands and is stated prominently wherever results are shown: public test sets (FLEURS) may appear in engine training data, so Track A connects to vendor-claimed numbers and public leaderboards rather than proving real-world accuracy (§4). The contamination question is real; this benchmark now answers it by disclosure, not by measurement. Anyone may record their own contamination-proof audio and run the full published pipeline on it via §8 — the §4 Track B design is CC-BY 4.0 like the rest of the documents and may serve as a recipe.

**Mechanical edits carried by this amendment.** §4 and §9 receive a dated pointer to this amendment (no frozen text is deleted); §8's `TRACK=<a|b>` switch and Track B audio references become vacuous for v1; the leaderboard banner changes from "Track B is pending" to the v1-is-Track-A-only wording; README status updated. No scoring, normalization, or data change accompanies this amendment; `results/scores.json` is untouched; the dual-table obligation is not triggered.
