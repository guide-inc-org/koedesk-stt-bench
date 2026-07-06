#!/usr/bin/env python3
"""Upload hf/out/ to the Hugging Face Hub as dataset koedesk/stt-bench.

Requires a write token in $HF_TOKEN or ~/.koedesk-ops/hf-token.txt.

Two-step publish (the approval gate is the --public flag):
  python3 hf/upload_hf_dataset.py            # create private repo + upload
  python3 hf/upload_hf_dataset.py --public   # flip visibility to public
"""

import argparse
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi

REPO_ID = "koedesk/stt-bench"
OUT = Path(__file__).resolve().parent / "out"


def get_token() -> str:
    tok = os.environ.get("HF_TOKEN", "").strip()
    if not tok:
        p = Path.home() / ".koedesk-ops" / "hf-token.txt"
        if p.exists():
            tok = p.read_text().strip()
    if not tok:
        sys.exit("no token: set HF_TOKEN or write ~/.koedesk-ops/hf-token.txt")
    return tok


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--public", action="store_true", help="make the dataset public")
    ap.add_argument("--repo-id", default=REPO_ID)
    args = ap.parse_args()

    api = HfApi(token=get_token())

    if args.public:
        api.update_repo_settings(repo_id=args.repo_id, repo_type="dataset", private=False)
        print(f"https://huggingface.co/datasets/{args.repo_id} is now PUBLIC")
        return

    if not (OUT / "data" / "transcriptions.parquet").exists():
        sys.exit("hf/out/ not built — run make_hf_dataset.py first")

    api.create_repo(repo_id=args.repo_id, repo_type="dataset", private=True, exist_ok=True)
    api.upload_folder(
        folder_path=str(OUT),
        repo_id=args.repo_id,
        repo_type="dataset",
        commit_message="v1 Track A: 13 engines x 12 languages x 200 FLEURS utterances (2026-07-05 run)",
    )
    print(f"uploaded to https://huggingface.co/datasets/{args.repo_id} (private)")


if __name__ == "__main__":
    main()
