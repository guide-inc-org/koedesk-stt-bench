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
