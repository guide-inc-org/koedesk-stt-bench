"""normalizers/ja.py のテスト — PREREGISTRATION.md §5 (日本語正規化) 準拠確認。

このテストファイルは §5.5 が要求する
「あいまいなクラスは normalizers/<lang>/numbers_test.py 相当のファイルで列挙する」
を満たす、日本語の numbers_test.py 相当も兼ねる (漢数字変換のあいまいクラス
列挙は test_kanji_to_arabic_ambiguous_classes_left_untouched を参照)。
"""

from normalizers.ja import (
    cer_chars_ja,
    kanji_to_arabic,
    normalize_ja,
    tokenize_ja,
)


# --------------------------------------------------------------------------
# §5.5 数値等価性: 漢数字→算用数字
# --------------------------------------------------------------------------


def test_cardinal_78():
    assert kanji_to_arabic("七十八") == "78"
    assert normalize_ja("七十八") == "78"


def test_mixed_positional_33000_all_forms_equivalent():
    # 三万三千 / 3万3000 / 33000 は全て同一の正規化結果になる (§5.5 明記の例)。
    assert kanji_to_arabic("三万三千") == "33000"
    assert kanji_to_arabic("3万3000") == "33000"
    assert normalize_ja("三万三千") == normalize_ja("3万3000") == normalize_ja("33000") == "33000"


def test_ordinal_dai_nijuu():
    assert kanji_to_arabic("第二十") == "第20"
    assert normalize_ja("第二十") == "第20"


def test_ordinal_dai_ichi_single_digit():
    assert kanji_to_arabic("第一") == "第1"


def test_digit_style_year_2026():
    assert kanji_to_arabic("二〇二六") == "2026"
    assert normalize_ja("二〇二六") == "2026"


def test_positional_building_blocks():
    # 位取り計算の基本ブロック。
    assert kanji_to_arabic("十") == "10"
    assert kanji_to_arabic("二十") == "20"
    assert kanji_to_arabic("二十五") == "25"
    assert kanji_to_arabic("百") == "100"
    assert kanji_to_arabic("百五") == "105"
    assert kanji_to_arabic("三百") == "300"
    assert kanji_to_arabic("千") == "1000"
    assert kanji_to_arabic("三千五百") == "3500"


def test_number_with_unambiguous_counter_still_converts():
    # 数字 + 非あいまいな助数詞/単位は変換される (79万3千のような一律ブロックは誤り)。
    assert kanji_to_arabic("三万三千円") == "33000円"
    assert kanji_to_arabic("十五歳") == "15歳"
    assert kanji_to_arabic("二十一人") == "21人"  # 「二十一」+「人」は「一人」慣用句ではない


def test_digit_group_separator_removed():
    assert normalize_ja("33,000") == "33000"
    assert normalize_ja("１，２３４，５６７") == "1234567"


# --------------------------------------------------------------------------
# §5.5 あいまいクラスの列挙 — 意図的に変換しない (untouched) ことを保証する
# --------------------------------------------------------------------------

AMBIGUOUS_CLASSES = [
    "一人",   # 助数詞「ひとり」の慣用読み (人数の一 vs 「独り」の含意)
    "ひとり",  # かな書き。漢数字を含まないため元々対象外だが明示的に確認する
    "一つ",   # かな書き助数詞
    "一番",   # 「いちばん」— 数とは独立に語彙化 (「最も」の意)
    "一緒",   # 「いっしょ」— 数とは独立に語彙化 (「共に」の意)
    "一般",   # 「いっぱん」— 数とは独立に語彙化 (「普通」の意)
    "万一",   # 「まんいち」慣用句 (「もしも」の意)
    "二日",   # 日付「ふつか」/期間、あいまいな読みを持つ
]


def test_kanji_to_arabic_ambiguous_classes_left_untouched():
    for word in AMBIGUOUS_CLASSES:
        assert kanji_to_arabic(word) == word, f"{word!r} は変換されずに残るべき"


def test_normalize_ja_ambiguous_classes_left_untouched_in_context():
    # 文中でも同様にあいまいクラスは変換されないことを確認する。
    assert normalize_ja("友達と一緒に行く") == "友達と一緒に行く"
    assert normalize_ja("一般的な話") == "一般的な話"
    assert normalize_ja("万一に備える") == "万一に備える"
    assert normalize_ja("二日前のこと") == "二日前のこと"
    assert normalize_ja("一人で歩く") == "一人で歩く"
    assert normalize_ja("ひとりで歩く") == "ひとりで歩く"
    assert normalize_ja("りんごを一つ食べる") == "りんごを一つ食べる"
    assert normalize_ja("彼が一番だ") == "彼が一番だ"


# --------------------------------------------------------------------------
# §5 手順3: 記号・句読点の除去 (Unicode category P*/S*)
# --------------------------------------------------------------------------


def test_punctuation_removal_japanese_marks():
    assert normalize_ja("こんにちは、世界。") == "こんにちは 世界"
    assert normalize_ja("犬・猫・鳥") == "犬 猫 鳥"
    assert normalize_ja("「引用」と『書名』") == "引用 と 書名"
    assert normalize_ja("これは？本当に！") == "これは 本当に"


# --------------------------------------------------------------------------
# §5.6 長音記号統一 (ー lookalikes → U+30FC)、漢数字「一」は不可侵
# --------------------------------------------------------------------------


def test_chouon_lookalikes_unified_to_prolonged_sound_mark():
    correct = "コーヒー"
    lookalikes = [
        "コ‐ヒ‐",  # HYPHEN
        "コ‑ヒ‑",  # NON-BREAKING HYPHEN
        "コ‒ヒ‒",  # FIGURE DASH
        "コ–ヒ–",  # EN DASH
        "コ—ヒ—",  # EM DASH
        "コ―ヒ―",  # HORIZONTAL BAR
        "コ−ヒ−",  # MINUS SIGN
        "コ-ヒ-",             # ASCII HYPHEN-MINUS
        "コ－ヒ－",            # FULLWIDTH HYPHEN-MINUS (NFKC→ASCII手前で統一)
    ]
    for variant in lookalikes:
        assert normalize_ja(variant) == correct, f"{variant!r} -> {normalize_ja(variant)!r}"


def test_chouon_unification_does_not_touch_kanji_ichi():
    # 「一」(漢数字/漢字) はダッシュ類ではないため、長音統一処理の対象に一切ならない。
    assert normalize_ja("一") == "1"  # 漢数字変換の対象(単独) にはなるが、長音化はされない
    assert "ー" not in normalize_ja("一")


def test_hyphen_between_digits_is_not_chouon_and_becomes_token_boundary():
    # §5.4: 数字間のハイフンは punctuation として除去され、トークン境界(空白)になる。
    # 長音記号化されない (直前が数字であり、かな文字ではないため)。
    assert normalize_ja("25-30") == "25 30"


# --------------------------------------------------------------------------
# §5 手順1: NFKC (全角/半角統一) + 手順2: ケースフォールド
# --------------------------------------------------------------------------


def test_nfkc_fullwidth_latin_and_digits():
    assert normalize_ja("ＡＢＣ") == "abc"
    assert normalize_ja("１２３") == "123"
    assert normalize_ja("ＡＢＣ１２３") == "abc123"


# --------------------------------------------------------------------------
# §5 手順4: 空白畳み込み — 凍結仕様のあいまい性#1 (両論併記フラグ)
# --------------------------------------------------------------------------


def test_whitespace_collapse_default_keeps_single_spaces():
    # 分かち書きされたエンジン出力 (gemini-3.1-flash-lite で観測)。
    # 既定 (仕様文言どおり): 連続空白は単一スペースに畳み込むが、単語間の
    # 単一スペースそのものは残す。
    assert normalize_ja("敵対 的 環境") == "敵対 的 環境"
    assert normalize_ja("敵対   的    環境") == "敵対 的 環境"  # runの畳み込み確認
    assert normalize_ja("  敵対的環境  ") == "敵対的環境"  # strip確認


def test_whitespace_strip_all_flag_removes_internal_spaces_too():
    # フラグON: 改訂読み。分かち書き由来のスペースを全除去し、無スペースの
    # リファレンスとCERで公平に比較できるようにする。
    assert (
        normalize_ja("敵対 的 環境", strip_all_whitespace_for_cer=True)
        == "敵対的環境"
    )
    assert (
        normalize_ja("敵対的環境", strip_all_whitespace_for_cer=True)
        == "敵対的環境"
    )


def test_whitespace_both_modes_agree_when_no_internal_spaces():
    ref = "今日は良い天気です"
    assert normalize_ja(ref) == normalize_ja(ref, strip_all_whitespace_for_cer=True)


# --------------------------------------------------------------------------
# WERトークナイザ (fugashi + unidic-lite) / CER文字列
# --------------------------------------------------------------------------


def test_tokenize_ja_returns_surface_tokens():
    tokens = tokenize_ja(normalize_ja("今日は良い天気です"))
    assert tokens == ["今日", "は", "良い", "天気", "です"]


def test_tokenize_ja_after_number_conversion():
    tokens = tokenize_ja(normalize_ja("今日は三万三千円です"))
    assert "33000" in tokens
    assert "円" in tokens


def test_cer_chars_ja_is_character_sequence():
    normalized = normalize_ja("今日は良い天気です")
    assert cer_chars_ja(normalized) == list(normalized)
    assert "".join(cer_chars_ja(normalized)) == normalized


# --------------------------------------------------------------------------
# べき等性 (2回適用しても結果が変わらない)
# --------------------------------------------------------------------------


IDEMPOTENCE_SAMPLES = [
    "今日は三万三千円、コ-ヒ-を、飲む。",
    "敵対 的 環境",
    "第二十回、二〇二六年の発表。",
    "友達と一緒に、万一に備えて二日前から準備する。",
    "ＡＢＣ１２３ー－",
]


def test_idempotence_default_mode():
    for s in IDEMPOTENCE_SAMPLES:
        once = normalize_ja(s)
        twice = normalize_ja(once)
        assert once == twice, f"idempotence failed for {s!r}: {once!r} != {twice!r}"


def test_idempotence_strip_all_whitespace_mode():
    for s in IDEMPOTENCE_SAMPLES:
        once = normalize_ja(s, strip_all_whitespace_for_cer=True)
        twice = normalize_ja(once, strip_all_whitespace_for_cer=True)
        assert once == twice, f"idempotence failed for {s!r}: {once!r} != {twice!r}"


def test_unparseable_number_run_left_untouched():
    """STTハルシネーション由来の解析不能run (万の重複) はクラッシュせず不変。

    パイロットbatch実データ: gemini-2.5-flash が ja_0018 で「約1万万年前」を
    出力し ValueError で採点が落ちた実例 (2026-07-04)。§5.5の
    「曖昧・解析不能は触らない」方針でフォールバックする。
    """
    from normalizers.ja import kanji_to_arabic, normalize_ja

    assert kanji_to_arabic("約1万万年前") == "約1万万年前"
    # 正常な「1万」は引き続き変換される
    assert kanji_to_arabic("約1万年前") == "約10000年前"
    # normalize_ja 経由でもクラッシュしない
    assert "万万" in normalize_ja("約1万万年前", strip_all_whitespace_for_cer=True)
