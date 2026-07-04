"""
WER / CER のコアアルゴリズム (PREREGISTRATION §6「Scoring & statistics」の実装)。

- Alignment: token-level (WER) / character-level (CER) Levenshtein alignment、
  uniform costs (S=D=I=1)。§6 冒頭で明記された通り、コストはすべて 1。
- Aggregation: corpus-level rate = Σ(edit errors) / Σ(reference length)。
  utterance-level mean も secondary として提供する（§6「Aggregation」）。
- Empty output: 空の仮説(hyp)は全削除(all-deletions)として採点する。
  除外は絶対に行わない（§6「Empty output」）。

`edit_ops` は文字列(char sequence)にもトークンのリスト(WER用)にも同じ
インターフェースで使える汎用アルゴリズムとして実装する。Python の
`str` はイテレートすると1文字ずつの `list` と同じように振る舞うため、
`ref`/`hyp` に str を渡せばそのまま CER として、`list[str]` を渡せば
そのまま WER として動く。
"""
from __future__ import annotations

from typing import Sequence


def edit_ops(ref: Sequence, hyp: Sequence) -> dict:
    """ref → hyp への最小コスト編集操作を求め、内訳を返す。

    コストはすべて uniform (S=D=I=1)。戻り値:
      {"sub": int, "del": int, "ins": int, "ref_len": int}

    ref/hyp は `list[str]`（WER のトークン列）でも `str`（CER の文字列。
    Python の str は char のシーケンスとして扱える）でもよい。

    実装は素朴な O(n*m) DP + backtrace。ベンチのユーティランス単位/
    文字単位の長さでは十分高速。

    注記（アルゴリズム上の既知の性質。挙動として明示しておく）:
      コストが全て 1 なので、最小コスト経路上の (sub+del+ins) の合計は
      経路の選び方に依らず必ず dp[n][m]（= 編集距離そのもの）に一致する。
      一方で「一致する文字が1つも無い区間の入れ替わり」のような箇所では
      sub と del+ins の内訳自体に複数の最小経路が存在し得る（例: ref=[a,b],
      hyp=[b,a] は 2 sub とも 1 del+1 ins とも取れる。合計は常に 2）。
      本実装は「一致 > 置換 > 削除 > 挿入」の優先順で backtrace し、
      内訳を一意に決める。corpus_rate / utterance_mean_rate が使うのは
      合計値のみなので、この内訳の選び方はレート計算に一切影響しない。
    """
    n, m = len(ref), len(hyp)

    # dp[i][j] = ref[:i] を hyp[:j] に変換する最小コスト
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        dp[i][0] = i  # 全削除
    for j in range(1, m + 1):
        dp[0][j] = j  # 全挿入

    for i in range(1, n + 1):
        ref_i = ref[i - 1]
        for j in range(1, m + 1):
            if ref_i == hyp[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                sub = dp[i - 1][j - 1] + 1
                dele = dp[i - 1][j] + 1
                ins = dp[i][j - 1] + 1
                dp[i][j] = min(sub, dele, ins)

    # backtrace: 一致 > 置換 > 削除 > 挿入 の優先順（内訳の一意化のみに影響、合計には影響しない）
    i, j = n, m
    sub = dele = ins = 0
    while i > 0 or j > 0:
        if i > 0 and j > 0 and ref[i - 1] == hyp[j - 1] and dp[i][j] == dp[i - 1][j - 1]:
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            sub += 1
            i -= 1
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            dele += 1
            i -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            ins += 1
            j -= 1
        else:  # pragma: no cover - dp の不変条件が壊れない限り到達しない
            raise RuntimeError("edit_ops: backtrace failed to make progress")

    return {"sub": sub, "del": dele, "ins": ins, "ref_len": n}


def utterance_errors(ref_tokens: Sequence, hyp_tokens: Sequence) -> dict:
    """1 発話分の誤り内訳を返す（`edit_ops` と同じ shape）。

    §6「Empty output」: hyp_tokens が空でも `edit_ops` はそのまま
    全削除 (del == ref_len, sub == ins == 0) を返すため、ここで
    特別扱いは不要（除外もしない）。パイプラインが「発話単位」で
    呼び出す際の公開名として `edit_ops` をそのまま委譲する。
    """
    return edit_ops(ref_tokens, hyp_tokens)


def _utterance_rate(u: dict) -> float:
    ref_len = u["ref_len"]
    if ref_len == 0:
        # ref が空の発話は仕様に規定が無いエッジケース。分母0を避けるため
        # 誤りが無ければ 0.0、誤り（=すべて挿入）があれば 1.0 として扱う。
        return 1.0 if (u["sub"] + u["del"] + u["ins"]) > 0 else 0.0
    return (u["sub"] + u["del"] + u["ins"]) / ref_len


def corpus_rate(per_utt: list[dict]) -> float:
    """corpus-level rate = Σ(sub+del+ins) / Σ(ref_len)（§6「Aggregation」、headline）。"""
    total_errors = sum(u["sub"] + u["del"] + u["ins"] for u in per_utt)
    total_ref_len = sum(u["ref_len"] for u in per_utt)
    if total_ref_len == 0:
        return 0.0 if total_errors == 0 else 1.0
    return total_errors / total_ref_len


def utterance_mean_rate(per_utt: list[dict]) -> float:
    """utterance-level mean rate（§6「Aggregation」、secondary。headline ではない）。"""
    if not per_utt:
        return 0.0
    return sum(_utterance_rate(u) for u in per_utt) / len(per_utt)
