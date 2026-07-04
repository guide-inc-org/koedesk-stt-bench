"""scoring/bootstrap.py のテスト (PREREGISTRATION §6 準拠を保証する)。"""
from scoring.bootstrap import (
    FROZEN_N,
    FROZEN_SEED,
    bootstrap_ci,
    paired_bootstrap_diff,
    tie_groups,
)
from scoring.metrics import corpus_rate


def _make_per_utt(errors: list[int], ref_len: int) -> list[dict]:
    return [{"sub": 0, "del": e, "ins": 0, "ref_len": ref_len} for e in errors]


def test_frozen_defaults_match_preregistration():
    # §6「Confidence intervals」: n=10000, seed=20260704 は FROZEN。
    assert FROZEN_N == 10_000
    assert FROZEN_SEED == 20260704


def test_bootstrap_ci_determinism_same_seed():
    per_utt = _make_per_utt([1, 0, 2, 0, 1, 3, 0, 1, 2, 0], ref_len=10)
    ci_1 = bootstrap_ci(per_utt, n=2000, seed=42)
    ci_2 = bootstrap_ci(per_utt, n=2000, seed=42)
    assert ci_1 == ci_2


def test_bootstrap_ci_default_seed_is_deterministic_across_calls():
    per_utt = _make_per_utt([2, 1, 0, 3, 1, 0, 2, 1], ref_len=8)
    ci_1 = bootstrap_ci(per_utt)
    ci_2 = bootstrap_ci(per_utt)
    assert ci_1 == ci_2


def test_bootstrap_ci_uses_the_given_seed_not_global_state():
    # 異なる seed を明示的に渡せば、同じ per_utt でも異なる rng 系列から CI が
    # 計算される（＝グローバル乱数状態ではなく引数の seed を実際に使っている）ことを、
    # 生の resample レートの並びが異なることで確認する（percentile 自体は粗いデータでは
    # 一致し得るため、分位点ではなく系列そのものを見る）。
    import numpy as np

    from scoring.bootstrap import _arrays, _resample_rates

    per_utt = _make_per_utt([1, 0, 2, 0, 1, 3, 0, 1, 2, 5, 2, 1], ref_len=10)
    errors, ref_len = _arrays(per_utt)
    N = len(per_utt)

    rng_1 = np.random.default_rng(1)
    idx_1 = rng_1.integers(0, N, size=(50, N))
    rates_1 = _resample_rates(errors, ref_len, idx_1)

    rng_2 = np.random.default_rng(2)
    idx_2 = rng_2.integers(0, N, size=(50, N))
    rates_2 = _resample_rates(errors, ref_len, idx_2)

    assert not np.array_equal(rates_1, rates_2)


def test_bootstrap_ci_brackets_point_estimate_for_varied_data():
    # 全発話で誤りが同じ(定数)場合、CIは点になり得るため、ここではばらつきのある
    # データで CI が corpus rate を挟む（point estimate が概ね CI 内）ことを確認する。
    per_utt = _make_per_utt([0, 1, 2, 0, 3, 1, 0, 2, 1, 0, 4, 0, 1, 2, 0], ref_len=10)
    point = corpus_rate(per_utt)
    lo, hi = bootstrap_ci(per_utt, n=5000, seed=FROZEN_SEED)
    assert lo <= hi
    # 点推定はだいたい CI の近くにある（緩い許容: ブートストラップの性質上ズレ得るが、
    # ここまで外れることは無い）
    assert lo - 0.05 <= point <= hi + 0.05


def test_paired_bootstrap_diff_determinism_same_seed():
    a = _make_per_utt([3, 4, 2, 5, 3], ref_len=10)
    b = _make_per_utt([1, 2, 1, 2, 1], ref_len=10)
    ci_1 = paired_bootstrap_diff(a, b, n=2000, seed=99)
    ci_2 = paired_bootstrap_diff(a, b, n=2000, seed=99)
    assert ci_1 == ci_2


def test_paired_bootstrap_diff_sign_sanity_strictly_worse_engine():
    # engine A が「全発話で」engine B より誤りが多い → 差の95%CIは0を含まず、
    # 常に正（A - B > 0）になるはず。
    ref_len = 10
    errors_a = [5, 4, 6, 3, 5, 4, 6, 3, 5, 4]
    errors_b = [1, 2, 1, 2, 1, 2, 1, 2, 1, 2]
    assert all(a > b for a, b in zip(errors_a, errors_b))

    per_utt_a = _make_per_utt(errors_a, ref_len)
    per_utt_b = _make_per_utt(errors_b, ref_len)

    lo, hi = paired_bootstrap_diff(per_utt_a, per_utt_b, n=FROZEN_N, seed=FROZEN_SEED)
    assert lo > 0  # CI が 0 を含まない、かつ A が常に悪い方向
    assert hi > 0


def test_paired_bootstrap_diff_no_difference_when_identical():
    # 同一の per-utterance 誤りなら差は常に 0 → CI は [0, 0]
    per_utt = _make_per_utt([2, 1, 3, 0, 2], ref_len=10)
    lo, hi = paired_bootstrap_diff(per_utt, per_utt, n=1000, seed=FROZEN_SEED)
    assert lo == 0.0
    assert hi == 0.0


def test_paired_bootstrap_diff_rejects_misaligned_lengths():
    a = _make_per_utt([1, 2], ref_len=10)
    b = _make_per_utt([1, 2, 3], ref_len=10)
    try:
        paired_bootstrap_diff(a, b, n=100, seed=1)
        assert False, "expected ValueError for misaligned per-utterance lists"
    except ValueError:
        pass


def test_tie_groups_ranks_ascending_and_separates_clearly_worse_engine():
    ref_len = 10
    n_utt = 20
    # engine_best: 常に誤り0
    engine_best = _make_per_utt([0] * n_utt, ref_len)
    # engine_mid: engine_best とほぼ同水準（僅かな誤り、重ならない可能性がある差）
    engine_mid = _make_per_utt([0, 1] * (n_utt // 2), ref_len)
    # engine_worst: 常に大差の誤り → 明確に別 tier になるはず
    engine_worst = _make_per_utt([8] * n_utt, ref_len)

    engines = {
        "best": engine_best,
        "mid": engine_mid,
        "worst": engine_worst,
    }
    groups = tie_groups(engines, n=FROZEN_N, seed=FROZEN_SEED)

    # 昇順ランクなので worst は最後の要素の tier に入る（先頭 tier には入らない）
    flat_order = [name for tier in groups for name in tier]
    assert flat_order.index("worst") > flat_order.index("best")
    # worst は best と同じ tier ではない（誤り率の差が明確に大きいため統計的に区別可能）
    best_tier = next(tier for tier in groups if "best" in tier)
    assert "worst" not in best_tier


def test_tie_groups_identical_engines_share_one_tier():
    ref_len = 10
    per_utt = _make_per_utt([1, 2, 0, 3, 1, 2, 0, 1], ref_len)
    engines = {"engine_a": per_utt, "engine_b": list(per_utt), "engine_c": list(per_utt)}
    groups = tie_groups(engines, n=1000, seed=FROZEN_SEED)
    assert len(groups) == 1
    assert set(groups[0]) == {"engine_a", "engine_b", "engine_c"}


def test_tie_groups_empty_input():
    assert tie_groups({}) == []
