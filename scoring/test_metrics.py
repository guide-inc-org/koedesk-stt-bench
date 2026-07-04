"""scoring/metrics.py のテスト (PREREGISTRATION §6 準拠を保証する)。"""
from scoring.metrics import (
    corpus_rate,
    edit_ops,
    utterance_errors,
    utterance_mean_rate,
)


def test_single_substitution_wer():
    # ref="a b c" hyp="a x c" → 1 sub, WER = 1/3 (課題文で明示された既知ケース)
    ops = edit_ops(["a", "b", "c"], ["a", "x", "c"])
    assert ops == {"sub": 1, "del": 0, "ins": 0, "ref_len": 3}
    assert ops["sub"] + ops["del"] + ops["ins"] == 1
    assert (ops["sub"] + ops["del"] + ops["ins"]) / ops["ref_len"] == 1 / 3


def test_insertion_case():
    # hyp が ref より1トークン多い（末尾に余分な "c"）→ 1 insertion
    ops = edit_ops(["a", "b"], ["a", "b", "c"])
    assert ops == {"sub": 0, "del": 0, "ins": 1, "ref_len": 2}
    assert (ops["sub"] + ops["del"] + ops["ins"]) / ops["ref_len"] == 1 / 2


def test_deletion_case():
    # hyp が ref より1トークン少ない（中間の "b" が脱落）→ 1 deletion
    ops = edit_ops(["a", "b", "c"], ["a", "c"])
    assert ops == {"sub": 0, "del": 1, "ins": 0, "ref_len": 3}
    assert (ops["sub"] + ops["del"] + ops["ins"]) / ops["ref_len"] == 1 / 3


def test_exact_match_is_zero_errors():
    ops = edit_ops(["a", "b", "c"], ["a", "b", "c"])
    assert ops == {"sub": 0, "del": 0, "ins": 0, "ref_len": 3}


def test_empty_hypothesis_scores_all_deletions():
    # §6「Empty output」: 空の仮説は全削除として採点する。除外は絶対にしない。
    ops = edit_ops(["a", "b", "c"], [])
    assert ops == {"sub": 0, "del": 3, "ins": 0, "ref_len": 3}
    assert utterance_errors(["a", "b", "c"], []) == ops
    # 空の hyp を「除外」した場合との違いを明示するため rate も確認 (= 1.0、除外なら未定義/0 になり得た)
    assert corpus_rate([ops]) == 1.0


def test_empty_hypothesis_utterance_errors_alias():
    # utterance_errors は edit_ops と同じ shape を返す公開名であることを確認
    assert utterance_errors(["a"], ["a"]) == edit_ops(["a"], ["a"])


def test_both_empty_is_zero_errors():
    ops = edit_ops([], [])
    assert ops == {"sub": 0, "del": 0, "ins": 0, "ref_len": 0}


def test_cer_japanese_hand_computed_distance():
    # ref="敵対的環境コース" (8文字) vs hyp="敵対的環境構成" (7文字)。
    # 手計算: 先頭5文字「敵対的環境」は一致。残り ref="コース"(3) vs hyp="構成"(2) は
    # 共通文字が無いため編集距離 = max(3,2) = 3 (例: 2 sub + 1 del)。
    # よって全体の編集距離合計は 3、ref_len=8、CER=3/8。
    ref = "敵対的環境コース"
    hyp = "敵対的環境構成"
    ops = edit_ops(ref, hyp)
    assert ops["ref_len"] == 8
    total = ops["sub"] + ops["del"] + ops["ins"]
    # 内訳 (sub/del の配分) は最小コスト経路が複数存在し得る既知のケース
    # (edit_ops のdocstring参照) なので、合計とrefのみを厳密に検証する。
    assert total == 3
    assert total / ops["ref_len"] == 3 / 8


def test_corpus_rate_aggregation():
    # §6「Aggregation」: corpus-level rate = Σ(errors) / Σ(ref_len)
    per_utt = [
        {"sub": 1, "del": 0, "ins": 0, "ref_len": 3},  # rate 1/3
        {"sub": 0, "del": 1, "ins": 1, "ref_len": 5},  # rate 2/5
    ]
    # Σerrors = 1 + 2 = 3, Σref_len = 3 + 5 = 8
    assert corpus_rate(per_utt) == 3 / 8


def test_corpus_rate_is_not_mean_of_utterance_rates():
    # corpus rate (長さ加重) と utterance mean rate (単純平均) が異なることを保証する
    # （§6: 両方とも報告するが headline は corpus rate）
    per_utt = [
        {"sub": 1, "del": 0, "ins": 0, "ref_len": 1},  # rate 1.0, 短い発話
        {"sub": 0, "del": 0, "ins": 0, "ref_len": 99},  # rate 0.0, 長い発話
    ]
    assert corpus_rate(per_utt) == 1 / 100
    assert utterance_mean_rate(per_utt) == (1.0 + 0.0) / 2


def test_utterance_mean_rate_secondary_metric():
    per_utt = [
        {"sub": 1, "del": 0, "ins": 0, "ref_len": 3},  # 1/3
        {"sub": 0, "del": 1, "ins": 1, "ref_len": 5},  # 2/5
    ]
    expected = ((1 / 3) + (2 / 5)) / 2
    assert utterance_mean_rate(per_utt) == expected


def test_corpus_rate_empty_list_and_zero_reflen_do_not_crash():
    assert corpus_rate([]) == 0.0
    assert utterance_mean_rate([]) == 0.0
