"""
ノンパラメトリック・ブートストラップ (PREREGISTRATION §6「Confidence intervals」
「Pairwise comparison」の実装)。

- n = 10,000, seed = 20260704 は §6 で FROZEN と明記されているため、
  関数のデフォルト引数にハードコードする（呼び出し側が変える理由は無い運用だが、
  再現性検証やテストの高速化のために上書き可能な引数として残す）。
- 乱数生成器は `numpy.random.default_rng(seed)`（指定どおり）。
- resampling の単位は「発話 (utterance)」。§6「Confidence intervals」
  「nonparametric bootstrap resampling utterances with replacement」。
- percentile method（2.5 / 97.5）。
- Pairwise comparison は同じ発話集合に対する paired bootstrap
  （同じリサンプルのインデックスを両エンジンに適用する）で、
  95% CI が 0 を含むかどうかで "distinguishable" を判定する（§6）。
"""
from __future__ import annotations

import numpy as np

from scoring.metrics import corpus_rate

FROZEN_N = 10_000
FROZEN_SEED = 20260704


def _arrays(per_utt: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """per-utterance dict のリストから (errors, ref_len) の numpy 配列を作る。"""
    errors = np.array([u["sub"] + u["del"] + u["ins"] for u in per_utt], dtype=np.float64)
    ref_len = np.array([u["ref_len"] for u in per_utt], dtype=np.float64)
    return errors, ref_len


def _resample_rates(errors: np.ndarray, ref_len: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """idx (n_resamples, N) の各行でリサンプルした corpus rate を返す。"""
    resampled_errors = errors[idx].sum(axis=1)
    resampled_ref_len = ref_len[idx].sum(axis=1)
    # ref_len 合計が 0 になるリサンプルは通常発生しない（各発話の ref_len > 0 が前提）が、
    # 念のためゼロ割りを避ける。
    with np.errstate(divide="ignore", invalid="ignore"):
        rates = np.where(resampled_ref_len > 0, resampled_errors / resampled_ref_len, 0.0)
    return rates


def bootstrap_ci(
    per_utt: list[dict], n: int = FROZEN_N, seed: int = FROZEN_SEED
) -> tuple[float, float]:
    """corpus rate の 95% ブートストラップ CI (percentile method) を返す。

    §6「Confidence intervals」: nonparametric bootstrap resampling utterances
    with replacement, n=10000, seed=20260704, percentile method (2.5/97.5)。
    """
    errors, ref_len = _arrays(per_utt)
    N = len(per_utt)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, N, size=(n, N))
    rates = _resample_rates(errors, ref_len, idx)
    lo, hi = np.percentile(rates, [2.5, 97.5])
    return float(lo), float(hi)


def paired_bootstrap_diff(
    per_utt_a: list[dict],
    per_utt_b: list[dict],
    n: int = FROZEN_N,
    seed: int = FROZEN_SEED,
) -> tuple[float, float]:
    """(rate_a - rate_b) の 95% paired ブートストラップ CI を返す。

    §6「Pairwise comparison」: 同じ発話集合に対する paired bootstrap。
    per_utt_a と per_utt_b は発話インデックスで対応（aligned）している前提
    （同じ言語・トラックの同じ発話集合に対する2エンジン分の per-utterance 誤り）。
    同じリサンプルインデックスを両エンジンに適用することで pairing を保つ。
    """
    if len(per_utt_a) != len(per_utt_b):
        raise ValueError("paired_bootstrap_diff: per_utt_a/per_utt_b must be aligned (same length)")

    errors_a, ref_len_a = _arrays(per_utt_a)
    errors_b, ref_len_b = _arrays(per_utt_b)
    N = len(per_utt_a)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, N, size=(n, N))

    rates_a = _resample_rates(errors_a, ref_len_a, idx)
    rates_b = _resample_rates(errors_b, ref_len_b, idx)
    diff = rates_a - rates_b

    lo, hi = np.percentile(diff, [2.5, 97.5])
    return float(lo), float(hi)


def tie_groups(
    engines: dict[str, list[dict]], n: int = FROZEN_N, seed: int = FROZEN_SEED
) -> list[list[str]]:
    """エンジンを corpus rate 昇順にランク付けし、タイ・グループへ束ねる。

    §6「Pairwise comparison」: エンジンは corpus rate で順位付けし、
    「その時点のグループのリーダー」との paired bootstrap 95% CI が 0 を
    含む限り同じ tier に留まる。含まなくなった時点でそのエンジンが
    新しい tier のリーダーになる（"walk down forming rank groups"）。

    リーダーとの比較であって「1つ上のエンジンとの比較」ではない点に注意
    （グループ内では group leader に対してのみ勝敗を主張しない、というのが
    §6 の "We never claim a win inside a tie group" の実装）。
    """
    ranked = sorted(engines.keys(), key=lambda name: corpus_rate(engines[name]))

    if not ranked:
        return []

    groups: list[list[str]] = []
    current_tier = [ranked[0]]
    tier_leader = ranked[0]

    for name in ranked[1:]:
        lo, hi = paired_bootstrap_diff(engines[name], engines[tier_leader], n=n, seed=seed)
        if lo <= 0.0 <= hi:
            # tier_leader との差が統計的に有意でない → 同じ tier
            current_tier.append(name)
        else:
            # 有意に区別できる → 新しい tier を開始し、このエンジンが新リーダー
            groups.append(current_tier)
            current_tier = [name]
            tier_leader = name

    groups.append(current_tier)
    return groups
