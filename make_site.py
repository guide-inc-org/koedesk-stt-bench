#!/usr/bin/env python3
"""
Leaderboard site generator (PREREGISTRATION §8/§9).

Reads results/scores.json (the only data source — no hand-edited numbers)
and writes site/index.html: a single self-contained static page (inline CSS,
no external requests). Deterministic: same scores.json → byte-identical HTML.

    python3 make_site.py
"""
from __future__ import annotations

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SCORES = os.path.join(ROOT, "results", "scores.json")
OUT_DIR = os.path.join(ROOT, "site")
OUT = os.path.join(OUT_DIR, "index.html")

REPO_URL = "https://github.com/guide-inc-org/koedesk-stt-bench"

ENGINE_NAMES = {
    "elevenlabs": "ElevenLabs Scribe v2",
    "openai": "OpenAI gpt-4o-transcribe",
    "whisper1": "OpenAI whisper-1",
    "google_stt_v2": "Google STT v2 (Chirp 3)",
    "deepgram": "Deepgram Nova-3",
    "mai_transcribe": "Microsoft MAI Transcribe (Azure Speech)",
    "amivoice": "AmiVoice (会話_汎用)",
    "mistral_voxtral": "Mistral Voxtral Mini Transcribe V2",
    "gemini": "Gemini 2.5 Flash",
    "gemini_25_pro": "Gemini 2.5 Pro",
    "gemini_31_flash_lite": "Gemini 3.1 Flash-Lite",
    "gemini_31_pro": "Gemini 3.1 Pro (preview)",
    "gemini_35_flash": "Gemini 3.5 Flash",
}

LANG_NAMES = {
    "ja": "Japanese", "en": "English", "zh": "Chinese (Mandarin, simplified)",
    "ko": "Korean", "vi": "Vietnamese", "id": "Indonesian", "th": "Thai",
    "de": "German", "fr": "French", "es": "Spanish", "pt": "Portuguese (BR)",
    "ru": "Russian",
}
LANG_ORDER = ["ja", "en", "zh", "ko", "vi", "id", "th", "de", "fr", "es", "pt", "ru"]

NOTES = [
    ("scope", "Track A uses FLEURS (public test set), 200 utterances × 12 languages, "
     "delivered to every engine as the identical 16-bit PCM file peak-normalized to "
     "−6 dBFS (PREREGISTRATION §4). Public test sets may appear in engine training "
     "data; Track B (fresh 2026 audio, contamination-proof) is the headline question "
     "of this benchmark and is pending."),
    ("coverage", "AmiVoice participates in Japanese only (§2). Mistral Voxtral covers "
     "9 of 12 languages — Vietnamese, Indonesian and Thai are not supported by the "
     "API and are shown as “not supported”, not as failures (Amendment 5)."),
    ("thai", "Thai has no word segmentation; WER is not defined for it (§5.6) and its "
     "column shows “—”. CER is the Thai headline."),
    ("empty", "An engine returning empty text scores all-deletions and is never "
     "excluded (§6) — excluding empties is the classic way to launder a bad engine."),
    ("gemini25zh", "Gemini 2.5 Pro / Chinese includes one utterance (zh_0192) where "
     "the engine returned ≈4,800 characters of English reasoning text instead of a "
     "transcript (finish_reason=stop, complete response). Published as measured per "
     "R-2.4/§7: engine behavior under preregistered default parameters is the thing "
     "being measured. Without that single utterance the cell's CER would be 0.0645; "
     "with it, 0.4834. This is a real failure mode of LLM-type STT engines."),
    ("gloss", "13/200 FLEURS Chinese references embed parenthetical English glosses "
     "that are not spoken in the audio (e.g. “罗兰多·门多萨 (Rolando Mendoza)”). "
     "This inflates CER equally for every engine and does not affect ranking."),
    ("gateway", "The five Gemini variants are called through Cloudflare AI Gateway "
     "(unified billing); their latency figures include the gateway hop. Accuracy is "
     "unaffected."),
    ("latency", "RTF = request wall-clock seconds ÷ audio seconds, measured from one "
     "machine (Mac mini, Tokyo-region ISP). Informational, not a ranking axis (§6)."),
    ("price", "Prices are vendor list prices per audio-hour at run date. “—” means "
     "the vendor has no per-hour list price (token-priced Gemini variants; AmiVoice "
     "measured on its free tier)."),
]


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.2f}"


def ci(block: dict | None) -> str:
    if not block:
        return "—"
    lo, hi = block["ci95"]
    return f"{100 * block['corpus_rate']:.2f} <span class=\"ci\">({100 * lo:.2f}–{100 * hi:.2f})</span>"


def engine_label(key: str) -> str:
    name = esc(ENGINE_NAMES.get(key, key))
    if key == "elevenlabs":
        name += ' <span class="koedesk-tag" title="Conflict of interest: koedesk uses this engine">used by koedesk</span>'
    return name


def render(scores: dict) -> str:
    track = scores["tracks"]["a"]
    langs = [l for l in LANG_ORDER if l in track]

    # ---- overview matrix: engine × language tier number
    tiers_by_lang: dict[str, dict[str, int]] = {}
    engines_seen: set[str] = set()
    for lang in langs:
        node = track[lang]
        m = {}
        for tier_i, tier in enumerate(node["tie_groups"], 1):
            for e in tier:
                m[e] = tier_i
        tiers_by_lang[lang] = m
        engines_seen.update(node["engines"].keys())

    def t1_count(e: str) -> int:
        return sum(1 for lang in langs if tiers_by_lang[lang].get(e) == 1)

    matrix_engines = sorted(engines_seen, key=lambda e: (-t1_count(e), e))

    matrix_rows = []
    for e in matrix_engines:
        cells = []
        for lang in langs:
            t = tiers_by_lang[lang].get(e)
            if t is None:
                supported = e in track[lang]["engines"]
                cells.append(f'<td class="na">{"·" if supported else "n/a"}</td>')
            else:
                cls = f"t{min(t, 4)}"
                cells.append(f'<td class="{cls}">T{t}</td>')
        matrix_rows.append(
            f"<tr><th>{engine_label(e)}</th>{''.join(cells)}"
            f'<td class="t1count">{t1_count(e)}</td></tr>'
        )

    matrix_html = f"""
<table class="matrix">
<thead><tr><th>Engine</th>{''.join(f'<th>{esc(l)}</th>' for l in langs)}<th>#T1</th></tr></thead>
<tbody>{''.join(matrix_rows)}</tbody>
</table>"""

    # ---- per-language sections
    lang_sections = []
    for lang in langs:
        node = track[lang]
        headline = node["headline_metric"]
        other = "wer" if headline == "cer" else "cer"
        rows = []
        for tier_i, tier in enumerate(node["tie_groups"], 1):
            for j, e in enumerate(tier):
                c = node["engines"][e]
                tier_cell = (
                    f'<td class="tier t{min(tier_i, 4)}" rowspan="{len(tier)}">T{tier_i}</td>'
                    if j == 0 else ""
                )
                price = c.get("price_per_audio_hour_usd")
                rows.append(
                    "<tr>"
                    + tier_cell
                    + f"<td class=\"engine\">{engine_label(e)}"
                    + f"<div class=\"model\">{esc(', '.join(c['model_ids']) or '—')}</div></td>"
                    + f"<td class=\"num\">{ci(c[headline])}</td>"
                    + f"<td class=\"num\">{ci(c[other])}</td>"
                    + f"<td class=\"num\">{c['empty_transcripts']}</td>"
                    + f"<td class=\"num\">{c['rtf_p50']:.2f} / {c['rtf_p90']:.2f}</td>"
                    + f"<td class=\"num\">{'—' if price is None else f'${price:.3f}'}</td>"
                    + f"<td class=\"num\">{esc(', '.join(c['run_dates']))}</td>"
                    + "</tr>"
                )
        n_utt = next(iter(node["engines"].values()))["n_utterances"]
        lang_sections.append(f"""
<section id="{esc(lang)}">
<h3>{esc(LANG_NAMES[lang])} <span class="langmeta">headline: {headline.upper()} · {n_utt} utterances</span></h3>
<div class="tablewrap"><table>
<thead><tr><th>Tier</th><th>Engine</th><th>{headline.upper()} % (95% CI)</th>
<th>{other.upper()} % (95% CI)</th><th>Empty</th><th>RTF p50/p90</th>
<th>$ / audio-hr</th><th>Run date</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>
</section>""")

    notes_html = "".join(
        f'<li id="note-{esc(k)}">{v}</li>' for k, v in NOTES
    )

    return f"""<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>koedesk STT Bench — Track A results</title>
<style>
:root {{
  --bg: #ffffff; --fg: #1a1d21; --muted: #6b7280; --line: #e5e7eb;
  --card: #f8fafc; --t1: #dcfce7; --t1fg: #14532d; --t2: #fef9c3; --t2fg: #713f12;
  --t3: #ffedd5; --t3fg: #7c2d12; --t4: #fee2e2; --t4fg: #7f1d1d;
  --accent: #0f766e; --tag: #0f766e;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0f1214; --fg: #e5e7eb; --muted: #9ca3af; --line: #2a2f36;
    --card: #171b1f; --t1: #103822; --t1fg: #86efac; --t2: #3a3311; --t2fg: #fde047;
    --t3: #3b2410; --t3fg: #fdba74; --t4: #3b1414; --t4fg: #fca5a5;
    --accent: #2dd4bf; --tag: #2dd4bf;
  }}
}}
:root[data-theme="light"] {{
  --bg: #ffffff; --fg: #1a1d21; --muted: #6b7280; --line: #e5e7eb;
  --card: #f8fafc; --t1: #dcfce7; --t1fg: #14532d; --t2: #fef9c3; --t2fg: #713f12;
  --t3: #ffedd5; --t3fg: #7c2d12; --t4: #fee2e2; --t4fg: #7f1d1d;
  --accent: #0f766e; --tag: #0f766e;
}}
:root[data-theme="dark"] {{
  --bg: #0f1214; --fg: #e5e7eb; --muted: #9ca3af; --line: #2a2f36;
  --card: #171b1f; --t1: #103822; --t1fg: #86efac; --t2: #3a3311; --t2fg: #fde047;
  --t3: #3b2410; --t3fg: #fdba74; --t4: #3b1414; --t4fg: #fca5a5;
  --accent: #2dd4bf; --tag: #2dd4bf;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0 auto; max-width: 1080px; padding: 24px 16px 64px;
  background: var(--bg); color: var(--fg);
  font: 15px/1.55 -apple-system, "Segoe UI", Roboto, "Hiragino Sans", sans-serif; }}
h1 {{ font-size: 1.7em; margin: 0 0 4px; }}
h2 {{ font-size: 1.25em; margin: 40px 0 8px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }}
h3 {{ font-size: 1.1em; margin: 28px 0 8px; }}
a {{ color: var(--accent); }}
.subtitle {{ color: var(--muted); margin: 0 0 16px; }}
.coi {{ background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--accent);
  padding: 12px 16px; border-radius: 8px; margin: 16px 0; }}
.trackb {{ background: var(--card); border: 1px solid var(--line); padding: 10px 16px;
  border-radius: 8px; margin: 12px 0; color: var(--muted); }}
.tablewrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.92em; }}
th, td {{ border: 1px solid var(--line); padding: 6px 9px; text-align: left; vertical-align: top; }}
thead th {{ background: var(--card); }}
td.num {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
td.tier {{ text-align: center; font-weight: 700; vertical-align: middle; }}
.t1 {{ background: var(--t1); color: var(--t1fg); }}
.t2 {{ background: var(--t2); color: var(--t2fg); }}
.t3 {{ background: var(--t3); color: var(--t3fg); }}
.t4 {{ background: var(--t4); color: var(--t4fg); }}
.matrix td {{ text-align: center; font-weight: 600; }}
.matrix td.na {{ color: var(--muted); font-weight: 400; }}
.matrix td.t1count {{ font-weight: 700; }}
.ci {{ color: var(--muted); font-size: 0.88em; }}
.model {{ color: var(--muted); font-size: 0.82em; }}
.langmeta {{ color: var(--muted); font-weight: 400; font-size: 0.8em; }}
.koedesk-tag {{ background: var(--tag); color: var(--bg); border-radius: 4px;
  padding: 1px 6px; font-size: 0.72em; font-weight: 600; white-space: nowrap; }}
.notes li {{ margin-bottom: 8px; }}
code {{ background: var(--card); border: 1px solid var(--line); border-radius: 4px;
  padding: 1px 5px; font-size: 0.9em; }}
footer {{ margin-top: 48px; color: var(--muted); font-size: 0.88em;
  border-top: 1px solid var(--line); padding-top: 16px; }}
</style>

<h1>koedesk STT Bench</h1>
<p class="subtitle">Multilingual speech-to-text accuracy, measured under a
<a href="{REPO_URL}/blob/main/PREREGISTRATION.md">preregistered methodology</a> —
Track A (FLEURS), 13 hosted engine variants × 12 languages × 200 utterances.</p>

<div class="coi"><strong>Conflict of interest, stated up front:</strong> this benchmark is
built and funded by <a href="https://koedesk.app">koedesk</a>, a dictation product that uses
ElevenLabs Scribe v2. We do not pretend to be neutral — instead, everything you need to
distrust us and re-run the benchmark yourself is published: the methodology (committed
<em>before</em> the headline runs — see the
<a href="{REPO_URL}/commits/main/PREREGISTRATION.md">commit history</a>), every raw API
response (<a href="{REPO_URL}/tree/main/results/raw">results/raw</a>), all scoring code, and
the <a href="{REPO_URL}/blob/main/tos-audit.md">terms-of-service audit</a> that decided which
engines could be included at all. Where Scribe loses, that result is published unchanged.</div>

<div class="trackb"><strong>Track B is pending.</strong> Track A uses public test sets that
engines may have trained on; the benchmark's headline question — does the ranking survive on
fresh, contamination-proof 2026 audio? — is answered by Track B, which will be published here
with the Track A ⇄ Track B divergence reported prominently (§9).</div>

<h2>How to read the tables</h2>
<p>Engines are ranked per language into <strong>tie groups</strong> (T1, T2, …): an engine
shares a tier when a paired bootstrap (n=10,000, seed frozen at preregistration) cannot
statistically distinguish it from the tier leader (95% CI of the paired difference includes
zero). <strong>Differences inside a tier are not statistically meaningful — including for
Scribe v2.</strong> The headline metric is CER for Japanese, Chinese and Thai, WER for the
other nine languages; both are always shown. Lower is better.</p>

<h2>Overview — tier per language</h2>
<div class="tablewrap">{matrix_html}</div>
<p class="subtitle">“n/a” = the engine does not support that language (AmiVoice: Japanese
only; Voxtral: no vi/id/th). #T1 counts languages where the engine is in the top tier.</p>

<h2>Per-language results — Track A (FLEURS)</h2>
{''.join(lang_sections)}

<h2>Notes &amp; known artifacts</h2>
<ul class="notes">{notes_html}</ul>

<h2>Reproduce / audit</h2>
<p>Everything is in <a href="{REPO_URL}">the repository</a>: raw API responses for all
28,400 utterances, frozen normalizers and scoring code with tests, the
<a href="{REPO_URL}/blob/main/AMENDMENTS.md">append-only amendment log</a>, and
<code>make_scores.py</code> / <code>make_site.py</code> which regenerate
<code>results/scores.json</code> and this page deterministically — no hand-edited numbers.
Re-running any cell needs only your own API keys.</p>

<footer>
Run window: 2026-07-05 (UTC), single machine (Mac mini, Tokyo-region ISP).
Next scheduled refresh: quarterly (2026-10).
Code: MIT · documents &amp; this page: CC-BY 4.0 · © 2026
<a href="https://koedesk.app">koedesk</a> (Guide Inc.)
</footer>
"""


def main() -> None:
    with open(SCORES, encoding="utf-8") as f:
        scores = json.load(f)
    os.makedirs(OUT_DIR, exist_ok=True)
    html_text = render(scores)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n<html lang=\"en\">\n<head>\n")
        # <head>/<body> split: everything up to </style> belongs in head
        head, _, body = html_text.partition("</style>")
        f.write(head + "</style>\n</head>\n<body>")
        f.write(body)
        f.write("\n</body>\n</html>\n")
    print(f"wrote {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
