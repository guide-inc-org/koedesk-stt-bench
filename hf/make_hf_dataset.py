#!/usr/bin/env python3
"""Build the Hugging Face dataset package from results/raw + results/scores.json.

Deterministic: same inputs -> byte-identical parquet output (fixed row order,
fixed column order, no timestamps injected). Run twice and diff to verify.

Output layout (hf/out/):
  README.md                  dataset card (copied from hf/README.md)
  data/transcriptions.parquet   28,400 rows, one per (engine, lang, utterance)
  data/cell_scores.parquet      142 rows, one per (engine, lang) cell
  scores.json                verbatim copy of results/scores.json

Usage:
  python3 hf/make_hf_dataset.py          # build into hf/out/
"""

import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "results" / "raw"
SCORES = ROOT / "results" / "scores.json"
CARD = ROOT / "hf" / "README.md"
OUT = ROOT / "hf" / "out"

EXPECTED_ROWS = 28_400
EXPECTED_CELLS = 142
UTTS_PER_CELL = 200


def build_transcriptions() -> pd.DataFrame:
    rows = []
    for eng_dir in sorted(RAW.iterdir()):
        if not eng_dir.is_dir():
            continue
        engine = eng_dir.name
        for lang_dir in sorted((eng_dir / "a").iterdir()):
            lang = lang_dir.name
            files = sorted(lang_dir.glob("*.json"))
            if len(files) != UTTS_PER_CELL:
                sys.exit(f"cell {engine}/{lang}: {len(files)} files, expected {UTTS_PER_CELL}")
            for f in files:
                d = json.loads(f.read_text())
                rows.append(
                    {
                        "engine": engine,
                        "model_id": d.get("params", {}).get("model_id")
                        or d.get("params", {}).get("model")
                        or d.get("params", {}).get("grammarFileNames")
                        or "",
                        "lang": lang,
                        "utt_id": d["utt_id"],
                        "duration_sec": d.get("duration_sec"),
                        "ref_text_raw": d.get("ref_text_raw"),
                        "ref_text_normalized": d.get("ref_text_normalized"),
                        "hypothesis": d.get("text"),
                        "latency_sec": d.get("latency_sec"),
                        "timestamp_utc": d.get("timestamp_utc"),
                        "retries": d.get("retries", 0),
                        "error": json.dumps(d["error"], ensure_ascii=False, sort_keys=True)
                        if d.get("error") is not None
                        else None,
                        "params_json": json.dumps(d.get("params", {}), ensure_ascii=False, sort_keys=True),
                        "raw_response_json": json.dumps(
                            d.get("raw_response"), ensure_ascii=False, sort_keys=True
                        ),
                    }
                )
    df = pd.DataFrame(rows)
    df = df.sort_values(["engine", "lang", "utt_id"], kind="mergesort").reset_index(drop=True)
    return df


def build_cell_scores() -> pd.DataFrame:
    track = json.loads(SCORES.read_text())["tracks"]["a"]
    rows = []
    for lang in sorted(track):
        block = track[lang]
        tie_groups = block["tie_groups"]
        tier_of = {}
        for rank, group in enumerate(tie_groups, start=1):
            for member in group:
                tier_of[member] = rank
        for engine in sorted(block["engines"]):
            e = block["engines"][engine]

            def metric(block_key: str, field: str):
                m = e.get(block_key)
                if m is None:
                    return None
                if field.startswith("ci95_"):
                    return m["ci95"][0 if field.endswith("lo") else 1]
                return m[field]

            rows.append(
                {
                    "lang": lang,
                    "engine": engine,
                    "headline_metric": block["headline_metric"],
                    "n_utterances": e["n_utterances"],
                    "empty_transcripts": e["empty_transcripts"],
                    "model_ids": ";".join(e["model_ids"]),
                    "run_dates": ";".join(e["run_dates"]),
                    "price_per_audio_hour_usd": e.get("price_per_audio_hour_usd"),
                    "rtf_p50": e.get("rtf_p50"),
                    "rtf_p90": e.get("rtf_p90"),
                    "cer_corpus": metric("cer", "corpus_rate"),
                    "cer_utterance_mean": metric("cer", "utterance_mean"),
                    "cer_ci95_lo": metric("cer", "ci95_lo"),
                    "cer_ci95_hi": metric("cer", "ci95_hi"),
                    "wer_corpus": metric("wer", "corpus_rate"),
                    "wer_utterance_mean": metric("wer", "utterance_mean"),
                    "wer_ci95_lo": metric("wer", "ci95_lo"),
                    "wer_ci95_hi": metric("wer", "ci95_hi"),
                    "tie_group": tier_of[engine],
                    "tie_group_members": ";".join(
                        next(g for g in tie_groups if engine in g)
                    ),
                }
            )
    df = pd.DataFrame(rows)
    df = df.sort_values(["lang", "engine"], kind="mergesort").reset_index(drop=True)
    return df


def write_parquet(df: pd.DataFrame, path: Path) -> None:
    table = pa.Table.from_pandas(df, preserve_index=False)
    pq.write_table(
        table,
        path,
        compression="zstd",
        # determinism: no embedded creation timestamp beyond the fixed writer string
        data_page_size=1 << 20,
    )


def main() -> None:
    if not CARD.exists():
        sys.exit("hf/README.md (dataset card) is missing")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "data").mkdir(exist_ok=True)

    tr = build_transcriptions()
    if len(tr) != EXPECTED_ROWS:
        sys.exit(f"transcriptions: {len(tr)} rows, expected {EXPECTED_ROWS}")
    cells = tr.groupby(["engine", "lang"]).size()
    if len(cells) != EXPECTED_CELLS or not (cells == UTTS_PER_CELL).all():
        sys.exit(f"cell layout wrong: {len(cells)} cells")
    if tr["hypothesis"].isna().any():
        sys.exit("null hypothesis found")

    cs = build_cell_scores()
    if len(cs) != EXPECTED_CELLS:
        sys.exit(f"cell_scores: {len(cs)} rows, expected {EXPECTED_CELLS}")
    raw_cells = set(map(tuple, cells.reset_index()[["engine", "lang"]].values))
    score_cells = set(map(tuple, cs[["engine", "lang"]].values))
    if raw_cells != score_cells:
        sys.exit(f"cell mismatch raw vs scores: {raw_cells ^ score_cells}")

    write_parquet(tr, OUT / "data" / "transcriptions.parquet")
    write_parquet(cs, OUT / "data" / "cell_scores.parquet")
    shutil.copyfile(SCORES, OUT / "scores.json")
    shutil.copyfile(CARD, OUT / "README.md")

    print(f"transcriptions: {len(tr)} rows -> {OUT/'data'/'transcriptions.parquet'}")
    print(f"cell_scores:    {len(cs)} rows -> {OUT/'data'/'cell_scores.parquet'}")
    for p in sorted(OUT.rglob("*")):
        if p.is_file():
            print(f"  {p.relative_to(OUT)}  {p.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
