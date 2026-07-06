#!/usr/bin/env python3
"""
Leaderboard site generator (PREREGISTRATION §8/§9), 36-locale.

Reads results/scores.json (the only data source — no hand-edited numbers) and
i18n/{locale}.json UI strings, and writes:

    site/index.html            (en, default locale, with language-suggest banner)
    site/{locale}/index.html   (35 localized pages)

Locale set mirrors koedesk.app (36 locales). Numbers, engine names and tables
are locale-independent; only UI copy is translated. Missing keys fall back to
English. Deterministic: same inputs → byte-identical output.

    python3 make_site.py
"""
from __future__ import annotations

import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SCORES = os.path.join(ROOT, "results", "scores.json")
I18N_DIR = os.path.join(ROOT, "i18n")
OUT_DIR = os.path.join(ROOT, "site")

REPO_URL = "https://github.com/guide-inc-org/koedesk-stt-bench"
HF_URL = "https://huggingface.co/datasets/koedesk/stt-bench"
BASE_URL = "https://koedesk.app"

DEFAULT_LOCALE = "en"
# Mirrors koedesk.app www/src/i18n/locales-list.mjs (36 locales).
LOCALES = [
    "en", "be", "bg", "bs", "ca", "cs", "da", "de", "el", "es",
    "et", "fi", "fr", "gl", "hr", "hu", "id", "is", "it", "ja",
    "kn", "lv", "mk", "ml", "ms", "nl", "no", "pl", "pt", "ro",
    "ru", "sk", "sv", "tr", "uk", "vi",
]
LOCALE_NAMES = {
    "en": "English", "ja": "日本語", "de": "Deutsch", "fr": "Français",
    "es": "Español", "it": "Italiano", "pt": "Português", "nl": "Nederlands",
    "ru": "Русский", "uk": "Українська", "pl": "Polski", "tr": "Türkçe",
    "vi": "Tiếng Việt", "id": "Bahasa Indonesia", "ms": "Bahasa Melayu",
    "cs": "Čeština", "sk": "Slovenčina", "da": "Dansk", "sv": "Svenska",
    "no": "Norsk", "fi": "Suomi", "hu": "Magyar", "ro": "Română",
    "el": "Ελληνικά", "bg": "Български", "be": "Беларуская", "bs": "Bosanski",
    "hr": "Hrvatski", "mk": "Македонски", "is": "Íslenska", "et": "Eesti",
    "lv": "Latviešu", "ca": "Català", "gl": "Galego", "kn": "ಕನ್ನಡ",
    "ml": "മലയാളം",
}

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

BENCH_LANGS = ["ja", "en", "zh", "ko", "vi", "id", "th", "de", "fr", "es", "pt", "ru"]

NOTE_KEYS = [
    "note_scope", "note_coverage", "note_thai", "note_empty",
    "note_gemini25zh", "note_gloss", "note_gateway", "note_latency", "note_price",
]

CSS = """
:root {
  --bg: #ffffff; --fg: #1a1d21; --muted: #6b7280; --line: #e5e7eb;
  --card: #f8fafc; --t1: #dcfce7; --t1fg: #14532d; --t2: #fef9c3; --t2fg: #713f12;
  --t3: #ffedd5; --t3fg: #7c2d12; --t4: #fee2e2; --t4fg: #7f1d1d;
  --accent: #0f766e; --tag: #0f766e;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1214; --fg: #e5e7eb; --muted: #9ca3af; --line: #2a2f36;
    --card: #171b1f; --t1: #103822; --t1fg: #86efac; --t2: #3a3311; --t2fg: #fde047;
    --t3: #3b2410; --t3fg: #fdba74; --t4: #3b1414; --t4fg: #fca5a5;
    --accent: #2dd4bf; --tag: #2dd4bf;
  }
}
:root[data-theme="light"] {
  --bg: #ffffff; --fg: #1a1d21; --muted: #6b7280; --line: #e5e7eb;
  --card: #f8fafc; --t1: #dcfce7; --t1fg: #14532d; --t2: #fef9c3; --t2fg: #713f12;
  --t3: #ffedd5; --t3fg: #7c2d12; --t4: #fee2e2; --t4fg: #7f1d1d;
  --accent: #0f766e; --tag: #0f766e;
}
:root[data-theme="dark"] {
  --bg: #0f1214; --fg: #e5e7eb; --muted: #9ca3af; --line: #2a2f36;
  --card: #171b1f; --t1: #103822; --t1fg: #86efac; --t2: #3a3311; --t2fg: #fde047;
  --t3: #3b2410; --t3fg: #fdba74; --t4: #3b1414; --t4fg: #fca5a5;
  --accent: #2dd4bf; --tag: #2dd4bf;
}
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 1080px; padding: 24px 16px 64px;
  background: var(--bg); color: var(--fg);
  font: 15px/1.55 -apple-system, "Segoe UI", Roboto, "Hiragino Sans", sans-serif; }
h1 { font-size: 1.7em; margin: 0 0 4px; }
h2 { font-size: 1.25em; margin: 40px 0 8px; border-bottom: 1px solid var(--line); padding-bottom: 6px; }
h3 { font-size: 1.1em; margin: 28px 0 8px; }
a { color: var(--accent); }
.topbar { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; flex-wrap: wrap; }
.lang-select { font-size: 0.85em; color: var(--muted); }
.lang-select select { background: var(--card); color: var(--fg); border: 1px solid var(--line);
  border-radius: 6px; padding: 3px 6px; font-size: 1em; }
.subtitle { color: var(--muted); margin: 0 0 16px; }
.coi { background: var(--card); border: 1px solid var(--line); border-left: 4px solid var(--accent);
  padding: 12px 16px; border-radius: 8px; margin: 16px 0; }
.trackb { background: var(--card); border: 1px solid var(--line); padding: 10px 16px;
  border-radius: 8px; margin: 12px 0; color: var(--muted); }
.suggest { background: var(--card); border: 1px solid var(--accent); padding: 10px 16px;
  border-radius: 8px; margin: 12px 0; display: flex; gap: 12px; align-items: center;
  justify-content: space-between; flex-wrap: wrap; }
/* Author display:flex would otherwise beat the UA's [hidden]{display:none},
   leaving an empty box when the JS decides not to show the suggestion. */
.suggest[hidden] { display: none; }
.suggest a { font-weight: 600; }
.suggest button { background: none; border: none; color: var(--muted); font-size: 1.1em; cursor: pointer; }
.tablewrap { overflow-x: auto; }
table { border-collapse: collapse; width: 100%; font-size: 0.92em; }
th, td { border: 1px solid var(--line); padding: 6px 9px; text-align: left; vertical-align: top; }
thead th { background: var(--card); }
td.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
td.tier { text-align: center; font-weight: 700; vertical-align: middle; }
.t1 { background: var(--t1); color: var(--t1fg); }
.t2 { background: var(--t2); color: var(--t2fg); }
.t3 { background: var(--t3); color: var(--t3fg); }
.t4 { background: var(--t4); color: var(--t4fg); }
.matrix td { text-align: center; font-weight: 600; }
.matrix td.na { color: var(--muted); font-weight: 400; }
.matrix td.t1count { font-weight: 700; }
.ci { color: var(--muted); font-size: 0.88em; }
.model { color: var(--muted); font-size: 0.82em; }
.langmeta { color: var(--muted); font-weight: 400; font-size: 0.8em; }
.koedesk-tag { background: var(--tag); color: var(--bg); border-radius: 4px;
  padding: 1px 6px; font-size: 0.72em; font-weight: 600; white-space: nowrap; }
.notes li { margin-bottom: 8px; }
code { background: var(--card); border: 1px solid var(--line); border-radius: 4px;
  padding: 1px 5px; font-size: 0.9em; }
footer { margin-top: 48px; color: var(--muted); font-size: 0.88em;
  border-top: 1px solid var(--line); padding-top: 16px; }
.locale-links { margin-top: 12px; font-size: 0.85em; color: var(--muted); line-height: 1.9; }
.locale-links a { white-space: nowrap; margin-right: 10px; }
"""


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def load_strings() -> dict[str, dict]:
    out = {}
    for loc in LOCALES:
        p = os.path.join(I18N_DIR, f"{loc}.json")
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                out[loc] = json.load(f)
        else:
            out[loc] = {}
    return out


class T:
    """Locale strings with en fallback and {repo} substitution."""

    def __init__(self, strings: dict, base: dict):
        self.strings = strings
        self.base = base

    def __call__(self, key: str, **kw) -> str:
        v = self.strings.get(key) or self.base[key]
        v = v.replace("{repo}", REPO_URL)
        for k, val in kw.items():
            v = v.replace("{" + k + "}", val)
        return v


def url_for(locale: str) -> str:
    # locale-first, mirroring koedesk.app page URLs (/ja/manifesto/ 等)
    if locale == DEFAULT_LOCALE:
        return f"{BASE_URL}/benchmark/"
    return f"{BASE_URL}/{locale}/benchmark/"


def ci_cell(block: dict | None) -> str:
    if not block:
        return "—"
    lo, hi = block["ci95"]
    return (
        f"{100 * block['corpus_rate']:.2f} "
        f"<span class=\"ci\">({100 * lo:.2f}–{100 * hi:.2f})</span>"
    )


def engine_label(key: str, t: T) -> str:
    name = esc(ENGINE_NAMES.get(key, key))
    if key == "elevenlabs":
        name += (
            f' <span class="koedesk-tag" title="{esc(t("used_by_koedesk_title"))}">'
            f"{esc(t('used_by_koedesk'))}</span>"
        )
    return name


def hreflang_links() -> str:
    parts = []
    for loc in LOCALES:
        parts.append(f'<link rel="alternate" hreflang="{loc}" href="{url_for(loc)}">')
    parts.append(f'<link rel="alternate" hreflang="x-default" href="{url_for(DEFAULT_LOCALE)}">')
    return "\n".join(parts)


def lang_selector(current: str, t: T) -> str:
    opts = []
    for loc in LOCALES:
        sel = " selected" if loc == current else ""
        opts.append(f'<option value="{url_for(loc)}"{sel}>{esc(LOCALE_NAMES[loc])}</option>')
    return (
        f'<div class="lang-select"><label>{esc(t("lang_label"))} '
        f'<select onchange="location.href=this.value">{"".join(opts)}</select></label></div>'
    )


def suggest_banner(all_strings: dict[str, dict]) -> str:
    """en ページのみ: LP と同じ lang_pin クッキー流儀のサジェストバナー。"""
    bundle = {}
    for loc in LOCALES:
        if loc == DEFAULT_LOCALE:
            continue
        s = all_strings.get(loc) or {}
        base = all_strings[DEFAULT_LOCALE]
        bundle[loc] = {
            "title": s.get("banner_title") or base["banner_title"],
            "switch": s.get("banner_switch") or base["banner_switch"],
            "name": LOCALE_NAMES[loc],
            "url": url_for(loc),
        }
    payload = json.dumps(bundle, ensure_ascii=False, sort_keys=True)
    return f"""
<div id="lang-suggest" class="suggest" hidden>
  <span data-slot="title"></span>
  <span><a data-slot="switch" href="#"></a>
  <button type="button" aria-label="Close" data-slot="close">×</button></span>
</div>
<script>
(function () {{
  try {{
    var bundle = {payload};
    if (document.cookie.indexOf('lang_pin=') >= 0) return;
    var pref = (navigator.language || 'en').toLowerCase().split('-')[0];
    var b = bundle[pref];
    if (!b) return;
    var el = document.getElementById('lang-suggest');
    el.querySelector('[data-slot="title"]').textContent = b.title.replace(/\\{{name\\}}/g, b.name);
    var sw = el.querySelector('[data-slot="switch"]');
    sw.textContent = b.switch.replace(/\\{{name\\}}/g, b.name);
    sw.href = b.url;
    sw.addEventListener('click', function () {{
      document.cookie = 'lang_pin=' + pref + '; Path=/; Max-Age=15552000; SameSite=Lax';
    }});
    el.querySelector('[data-slot="close"]').addEventListener('click', function () {{
      document.cookie = 'lang_pin=en; Path=/; Max-Age=15552000; SameSite=Lax';
      el.setAttribute('hidden', '');
    }});
    el.removeAttribute('hidden');
  }} catch (e) {{}}
}})();
</script>"""


def render(scores: dict, locale: str, t: T, all_strings: dict[str, dict]) -> str:
    track = scores["tracks"]["a"]
    langs = [l for l in BENCH_LANGS if l in track]

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
            tv = tiers_by_lang[lang].get(e)
            if tv is None:
                cells.append('<td class="na">n/a</td>')
            else:
                cells.append(f'<td class="t{min(tv, 4)}">T{tv}</td>')
        matrix_rows.append(
            f"<tr><th>{engine_label(e, t)}</th>{''.join(cells)}"
            f'<td class="t1count">{t1_count(e)}</td></tr>'
        )
    matrix_html = (
        '<table class="matrix"><thead><tr>'
        + f"<th>{esc(t('th_engine'))}</th>"
        + "".join(f"<th>{esc(l)}</th>" for l in langs)
        + "<th>#T1</th></tr></thead>"
        + f"<tbody>{''.join(matrix_rows)}</tbody></table>"
    )

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
                    "<tr>" + tier_cell
                    + f"<td class=\"engine\">{engine_label(e, t)}"
                    + f"<div class=\"model\">{esc(', '.join(c['model_ids']) or '—')}</div></td>"
                    + f"<td class=\"num\">{ci_cell(c[headline])}</td>"
                    + f"<td class=\"num\">{ci_cell(c[other])}</td>"
                    + f"<td class=\"num\">{c['empty_transcripts']}</td>"
                    + f"<td class=\"num\">{c['rtf_p50']:.2f} / {c['rtf_p90']:.2f}</td>"
                    + f"<td class=\"num\">{'—' if price is None else f'${price:.3f}'}</td>"
                    + f"<td class=\"num\">{esc(', '.join(c['run_dates']))}</td>"
                    + "</tr>"
                )
        n_utt = next(iter(node["engines"].values()))["n_utterances"]
        lang_sections.append(f"""
<section id="{esc(lang)}">
<h3>{esc(t('lang_' + lang))} <span class="langmeta">{esc(t('langmeta_headline'))}: {headline.upper()} · {n_utt} {esc(t('langmeta_utterances'))}</span></h3>
<div class="tablewrap"><table>
<thead><tr><th>{esc(t('th_tier'))}</th><th>{esc(t('th_engine'))}</th>
<th>{headline.upper()}{esc(t('th_ci_suffix'))}</th><th>{other.upper()}{esc(t('th_ci_suffix'))}</th>
<th>{esc(t('th_empty'))}</th><th>{esc(t('th_rtf'))}</th><th>{esc(t('th_price'))}</th>
<th>{esc(t('th_rundate'))}</th></tr></thead>
<tbody>{''.join(rows)}</tbody>
</table></div>
</section>""")

    notes_html = "".join(f"<li>{t(k)}</li>" for k in NOTE_KEYS)
    banner = suggest_banner(all_strings) if locale == DEFAULT_LOCALE else ""
    locale_links = "".join(
        f'<a href="{url_for(loc)}" hreflang="{loc}">{esc(LOCALE_NAMES[loc])}</a> '
        for loc in LOCALES
    )

    return f"""<!doctype html>
<html lang="{locale}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(t('page_title'))}</title>
<link rel="canonical" href="{url_for(locale)}">
{hreflang_links()}
<style>{CSS}</style>
</head>
<body>
<div class="topbar"><h1>{esc(t('site_h1'))}</h1>{lang_selector(locale, t)}</div>
<p class="subtitle">{t('subtitle')}</p>
{banner}
<div class="coi">{t('coi_html')}</div>
<div class="trackb">{t('trackb_html')}</div>

<h2>{esc(t('howto_h'))}</h2>
<p>{t('howto_html')}</p>

<h2>{esc(t('overview_h'))}</h2>
<div class="tablewrap">{matrix_html}</div>
<p class="subtitle">{t('overview_note')}</p>

<h2>{esc(t('perlang_h'))}</h2>
{''.join(lang_sections)}

<h2>{esc(t('notes_h'))}</h2>
<ul class="notes">{notes_html}</ul>

<h2>{esc(t('repro_h'))}</h2>
<p>{t('repro_html')}</p>

<footer>
<div><a href="{REPO_URL}">GitHub</a> · <a href="{HF_URL}">🤗 Hugging Face (raw data)</a></div>
{t('footer_html')}
<div class="locale-links">{locale_links}</div>
</footer>
</body>
</html>
"""


def main() -> None:
    with open(SCORES, encoding="utf-8") as f:
        scores = json.load(f)
    all_strings = load_strings()
    base = all_strings[DEFAULT_LOCALE]
    if not base:
        raise SystemExit("i18n/en.json is required")

    written = []
    for locale in LOCALES:
        t = T(all_strings[locale], base)
        html_text = render(scores, locale, t, all_strings)
        out = (
            os.path.join(OUT_DIR, "benchmark", "index.html")
            if locale == DEFAULT_LOCALE
            else os.path.join(OUT_DIR, locale, "benchmark", "index.html")
        )
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html_text)
        written.append(out)
    print(f"wrote {len(written)} pages under {OUT_DIR}", file=sys.stderr)


if __name__ == "__main__":
    main()
