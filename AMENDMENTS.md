# Amendments

Append-only, dated (PREREGISTRATION §9). Each amendment states the change, the reason, and carries the §5 obligation: headline tables are published under the amended rule **and** the pre-amendment rule side by side for every affected cell.

---

## Amendment 1 — §5.4 whitespace handling for unspaced scripts (2026-07-05)

**Change.** For languages whose reference orthography does not use inter-word whitespace (ja, zh, th), **all whitespace is removed** from both reference and hypothesis before CER computation. For spaced languages §5.4 stands as frozen (collapse runs to a single space; strip). WER is unaffected (tokenizers are whitespace-independent by construction).

**Reason — a spec defect found by the declared pilot (§7), not an outcome preference.** §5.4 as frozen says only "collapse runs to single space; strip", so inter-token spaces surviving in a hypothesis count as CER insertions against space-free references. The pilot showed this lets a *formatting* habit dominate a *transcription accuracy* metric: one engine (Gemini 3.1 Flash-Lite) emits token-spaced Japanese under the neutral fixed instruction required by R-2.3, and under the literal reading its pilot ja CER was inflated roughly eightfold by whitespace insertions alone (≈ +33 points), while every other engine moved by only 1–5 points from the same rule choice. A character-error metric in which spaces outweigh actual character errors does not measure what §1 declares is being measured.

**What this amendment does *not* do.** It does not absolve the behavior. Token-spaced CJK output is a real usability defect for dictation — such output requires post-processing before it can be inserted into Japanese text. This is recorded as a **standing auxiliary finding** (same class as the quiet-audio robustness finding in §4/§7): the engines that emit token-spaced Japanese are named in the results publication, with examples, outside the headline table. The dual-table obligation above additionally keeps the literal-rule numbers permanently visible.

**Scope note.** ko keeps §5.4 as frozen (Korean orthography uses inter-word spacing; spacing differences there are genuine orthographic choices, handled by WER/CER as-is).
