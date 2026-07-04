"""
英語テキスト正規化 (PREREGISTRATION §5 の実装)。

パイプライン:
  ステップ1-5 (`_normalize_steps_1_to_5`, 全言語共通の一般規則を英語向けに実装):
    1. Unicode NFKC 正規化
    2. ケースフォールディング
    3. 句読点・記号除去 (Unicode category P*/S*)。ただし語中アポストロフィ
       ("don't") は保持し、’→' に標準化する
    4. 空白の圧縮
    5. 数値等価化: 綴り数詞(基数・序数)→数字、桁区切り除去、
       範囲のハイフンはトークン境界化 (§5.5)
  ステップ6 (§5.6, `normalize_en`):
    ピン留めされた Whisper 公式 English normalizer (vendor/whisper_normalizers)
    をステップ1-5の出力の上に適用する。HF Open ASR Leaderboard との比較可能性
    のため。
  最終ステップ (§5.5 準拠の後処理 + 冪等性のためのクリーンアップ):
    a. Whisper normalizer は序数の接尾辞を意図的に残す ("twentieth"→"20th") が、
       §5.5 は「twentieth→20th→20」と明記し、序数は裸の数字で終わることを要求する。
       そのため数字トークンの st/nd/rd/th 接尾辞のみを最後に剥がす
       (複数形の "s" は対象外: "1960s" はそのまま)。
    b. Whisper normalizer は綴り通貨語を記号に変換することがある
       (例: "dollars"→"$")。ステップ3の「P*/S* 除去」の不変条件をここで
       再適用し、そのような記号を含め最終出力からステップ3対象の記号を
       すべて除去する (冪等性のため。詳細は `normalize_en` 内コメント参照)。

## ステップ順序に関する既知の調整 (§5.5 桁区切りとの整合)

PREREGISTRATION §5 はステップを 1→5 の番号順で並べているが、文字どおりの
逐次適用 (ステップ3の句読点除去を先に完了させてからステップ5の桁区切り除去
を行う) では "33,000"→"33000" という §5.5 で明記された等価性を満たせない。
理由: ステップ3の句読点除去はカンマを「トークン境界(空白)」に変換する
(§5.5 のハイフン→範囲境界の規則と同じ扱いのため)。すると "33,000" は
"33 000" という2トークンになり、そのあとステップ5の数値コンバータに
渡すと "33" と "000" が別々の数値として解釈され "33 0" という誤った結果
になってしまう(実装時に実際に確認した副作用)。

したがって「桁区切り除去」だけは、一般句読点除去(ステップ3)より前に、
カンマを空白ではなく完全削除する形で先に処理する。これは §5.5 が要求する
最終的な等価性 ("33,000" ≡ "33000") を満たすための、可観測な出力に影響
しない実装順の調整であり、規則の内容そのものを変えるものではない
(§5.5 で明示的に要求されている出力そのものを実現するために必要な調整)。
その他のステップ順序 (NFKC→ケースフォールド→句読点除去→空白圧縮→
綴り数詞変換) は §5 記載の順序どおり。

## 数値コンバータについて

§5.5 は「綴り数詞は言語ごとの決定論的な公開コンバータで数字に変換する」と
定める。英語について、この「決定論的で公開されたコンバータ」として
ピン留め済みの vendor/whisper_normalizers の `EnglishNumberNormalizer` を
再利用する(ステップ5とステップ6で同一のコンバータを使うことで、独自実装
との食い違いが生じない)。ステップ6 (`EnglishTextNormalizer`) は内部でも
同じコンバータを再度呼ぶが、ステップ5の時点で数字への変換が既に完了して
いるため冪等 (no-op) であることをテストで確認している。
"""
from __future__ import annotations

import re
import unicodedata

from .vendor.whisper_normalizers.english import (
    EnglishNumberNormalizer,
    EnglishTextNormalizer,
)

# 語中アポストロフィを一時退避するプレースホルダ。
# Private Use Area の文字を使う (通常の英文入力には現れず、
# Unicode category "Co" のため P*/S* 除去の対象にならない)。
_APOS_PLACEHOLDER = ""

_WHITESPACE_RE = re.compile(r"\s+")
_DIGIT_GROUP_SEP_RE = re.compile(r"(?<=\d),(?=\d)")
_WORD_INTERNAL_APOS_RE = re.compile(r"(?<=\w)'(?=\w)")
# §5.5 最終処理: 序数接尾辞のみ剥がす (複数形の "s" は対象外)
_ORDINAL_SUFFIX_RE = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b")

# ピン留めされたコンバータのインスタンスは1回だけ生成して使い回す
# (english.json の読み込みが1回で済む)。
_number_normalizer = EnglishNumberNormalizer()
_text_normalizer = EnglishTextNormalizer()


def _collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _strip_symbols_keep_apostrophe(text: str) -> str:
    """§5 ステップ3の句読点・記号除去 (P*/S*、語中アポストロフィは例外)。

    ステップ1-5の内部でも、§5.6のあとの最終クリーンアップでも共有して使う
    (下の `normalize_en` のコメント参照)。
    """
    text = text.replace("’", "'")
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = "".join(
        " " if unicodedata.category(ch)[0] in ("P", "S") else ch for ch in text
    )
    return text.replace(_APOS_PLACEHOLDER, "'")


def _normalize_steps_1_to_5(text: str) -> str:
    """PREREGISTRATION §5 ステップ1-5 (英語向け実装)。"""
    # 1. Unicode NFKC
    text = unicodedata.normalize("NFKC", text)

    # 2. ケースフォールディング
    text = text.casefold()

    # 5 (前倒し実行, 上記モジュールdocstring参照): 桁区切りのカンマを
    # トークン境界を作らずに削除する ("33,000"→"33000")。
    # ’→' の標準化はここで一度済ませておく (語中判定を単一のアポストロフィ
    # 文字で行うため。実際の除去+例外保持は _strip_symbols_keep_apostrophe)。
    text = text.replace("’", "'")
    text = _DIGIT_GROUP_SEP_RE.sub("", text)

    # 3. 句読点・記号除去 (P*/S*)。語中アポストロフィは例外的に保持する。
    text = _strip_symbols_keep_apostrophe(text)

    # 4. 空白圧縮
    text = _collapse_whitespace(text)

    # 5. 綴り数詞(基数・序数)→数字
    text = _number_normalizer(text)
    text = _collapse_whitespace(text)

    return text


def normalize_en(text: str) -> str:
    """PREREGISTRATION §5 (ステップ1-5 + §5.6 Whisper normalizer) を適用する。"""
    text = _normalize_steps_1_to_5(text)

    # §5.6: ピン留めされた Whisper English normalizer をステップ1-5の上に適用
    text = _text_normalizer(text)

    # §5.5 最終処理: 序数は裸の数字で終わる ("20th"→"20")。
    # Whisper normalizer は序数接尾辞を意図的に残す仕様のため、ここで剥がす。
    text = _ORDINAL_SUFFIX_RE.sub(r"\1", text)

    # 冪等性を保証する最終クリーンアップ (ステップ3の不変条件の再確認)。
    # Whisper normalizer は綴り通貨語 ("dollars"/"cents"/"pounds"/"euros") を
    # $/¢/£/€ のような記号に変換して埋め込むことがある (例:
    # "twenty-one dollars" → "$21")。これらの記号はステップ3が本来除去する
    # はずの Unicode category S* であり、ステップ3が既に完了した後で
    # Whisper normalizer 側が新たに生成したものに過ぎない。放置すると
    # normalize_en(normalize_en(x)) の2回目の呼び出しでは、この "$" が
    # 「元からある入力」としてステップ3で除去され、1回目の出力と食い違う
    # (冪等性が壊れる)。ステップ3の「P*/S* は語中アポストロフィ以外すべて
    # 除去する」という不変条件を最終出力にも適用し直すことで、
    # normalize_en の出力自体が常にステップ3をパススルーする不動点になり、
    # 冪等性が一般的に保証される。
    text = _strip_symbols_keep_apostrophe(text)
    text = _collapse_whitespace(text)

    return text


def tokenize_en(text: str) -> list[str]:
    """正規化済みテキストを空白分割する (WER 用)。"""
    normalized = normalize_en(text)
    if not normalized:
        return []
    return normalized.split(" ")
