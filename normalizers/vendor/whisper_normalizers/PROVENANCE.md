# Provenance — vendored Whisper text normalizers

PREREGISTRATION.md §5.6 pins en/de/fr/es/pt normalization to "the pinned Whisper
open-source normalizer" so results stay comparable with the HF Open ASR
Leaderboard. This directory is a verbatim vendor copy of the relevant files
from the `openai/whisper` GitHub repository, pinned at tag **`v20240930`**
(commit tagged `v20240930`, license MIT).

## Source files (fetched 2026-07-04)

| Vendored file | Source URL |
|---|---|
| `english.py` | https://raw.githubusercontent.com/openai/whisper/v20240930/whisper/normalizers/english.py |
| `basic.py` | https://raw.githubusercontent.com/openai/whisper/v20240930/whisper/normalizers/basic.py |
| `english.json` | https://raw.githubusercontent.com/openai/whisper/v20240930/whisper/normalizers/english.json |
| `__init__.py` | https://raw.githubusercontent.com/openai/whisper/v20240930/whisper/normalizers/__init__.py |

Retrieved with plain `curl` (no transformation) and diffed by eye against the
GitHub blob at the same tag before committing. No line of `english.py`,
`basic.py`, or `english.json` was edited — they are byte-for-byte copies of
the pinned tag.

## Adaptations made

**None to the vendored code itself.** The only change from the upstream
layout is packaging:

- Upstream lives at `whisper/normalizers/*` inside the full `openai/whisper`
  package (which pulls in torch, tiktoken, numpy, etc. — a heavyweight
  dependency we do not need just to run two pure-Python text-normalization
  modules). We vendor only the three normalizer files instead of taking a
  dependency on the whole `openai-whisper` PyPI package.
- `__init__.py` is copied unmodified; because the two source files
  (`english.py`, `basic.py`) sit in the same relative directory as upstream,
  its original relative imports (`from .basic import ...`,
  `from .english import ...`) resolve without any change.
- `english.py`'s own internal path lookup
  (`os.path.join(os.path.dirname(__file__), "english.json")`) also resolves
  unchanged, since `english.json` sits next to `english.py` here exactly as
  it does upstream.

## Third-party Python dependencies required by the vendored code

`english.py` imports `more_itertools` (for `windowed`); `basic.py` imports
`regex` (used only inside `BasicTextNormalizer.split_letters`, not on the
`EnglishTextNormalizer` code path we actually call, but the module-level
`import regex` still executes on import). Both were already present in the
target venv (`/Users/kondomasaki/kondo-daily-ops/projects/koedesk/stt-benchmark/pilot/venv`)
at the time of vendoring, so no `pip install` was needed:

- `regex==2026.6.28`
- `more-itertools==11.1.0`

(Recorded here per instruction in case the venv is rebuilt — pin these two
packages, or newer, when reproducing.)

## License

`openai/whisper` is MIT-licensed. The vendored files retain their original
content (including any in-file comments); this PROVENANCE.md and the
`normalizers/en.py` wrapper are the only new files we authored around them.
