"""normalizers/zh.py のテスト — PREREGISTRATION.md §5 (簡体中国語正規化) 準拠確認。

このテストファイルは §5.5 が要求する
「あいまいなクラスは normalizers/<lang>/numbers_test.py 相当のファイルで列挙する」
を満たす、簡体中国語の numbers_test.py 相当も兼ねる (数詞変換のあいまいクラス
列挙は TestAmbiguousClasses を参照)。

Amendment 1 (§5.4 改訂: zh は CER 前に全空白除去、凍結版と併記) の
二値フラグ両側の挙動も検証する。
"""

from normalizers.zh import (
    cer_chars_zh,
    normalize_zh,
    tokenize_zh,
    zh_numerals_to_arabic,
)


# --------------------------------------------------------------------------
# §5.5 数値等価性: 中国語数詞→算用数字
# --------------------------------------------------------------------------


class TestNumeralsToArabic:
    def test_cardinal_78(self):
        assert zh_numerals_to_arabic("七十八") == "78"
        assert normalize_zh("七十八") == "78"

    def test_mixed_positional_33000_all_forms_equivalent(self):
        # 三万三千 / 3万3000 / 33000 は全て同一の正規化結果になる (§5.5 の例の zh 版)。
        assert zh_numerals_to_arabic("三万三千") == "33000"
        assert zh_numerals_to_arabic("3万3000") == "33000"
        assert (
            normalize_zh("三万三千")
            == normalize_zh("3万3000")
            == normalize_zh("33000")
            == "33000"
        )

    def test_ordinal_di_ershi(self):
        # 序数接頭辞「第」は残したまま数字部分のみ変換 (ja の 第二十→第20 と同型)。
        assert zh_numerals_to_arabic("第二十") == "第20"
        assert zh_numerals_to_arabic("第一") == "第1"
        assert normalize_zh("第二十") == "第20"

    def test_digit_style_year_2026(self):
        # 桁読み (位取り文字を含まないrun)。zh では 零 も桁読みの 0 になる。
        assert zh_numerals_to_arabic("二〇二六") == "2026"
        assert zh_numerals_to_arabic("二零二六") == "2026"
        assert normalize_zh("二零二六") == "2026"

    def test_positional_building_blocks(self):
        # 係数を伴う位取り合成は変換される。裸の位取り文字単独 (十/百/千/万) は
        # zh.py docstring (d) のガードにより不変換 (TestBareUnitRunGuard 参照)。
        assert zh_numerals_to_arabic("二十") == "20"
        assert zh_numerals_to_arabic("二十五") == "25"
        assert zh_numerals_to_arabic("一百") == "100"
        assert zh_numerals_to_arabic("三百") == "300"
        assert zh_numerals_to_arabic("一千") == "1000"
        assert zh_numerals_to_arabic("三千五百") == "3500"
        assert zh_numerals_to_arabic("九万九千") == "99000"

    def test_zero_insertion_ling(self):
        # zh 固有の 零 挿入正書法 (位の飛びの標識)。ja には無い規則。
        assert zh_numerals_to_arabic("一百零五") == "105"
        assert zh_numerals_to_arabic("三万零五百") == "30500"
        assert zh_numerals_to_arabic("一千零一") == "1001"

    def test_liang_with_unit_converts(self):
        # 两 は位取り単位の直前の係数としてのみ 2 に変換 (zh 固有規則 (a))。
        assert zh_numerals_to_arabic("两千") == "2000"
        assert zh_numerals_to_arabic("两万三千") == "23000"
        assert zh_numerals_to_arabic("两百") == "200"

    def test_number_with_unambiguous_measure_word_still_converts(self):
        # 数字 + 非あいまいな量詞/単位は変換される (一律ブロックは誤り)。
        assert zh_numerals_to_arabic("三万三千元") == "33000元"
        assert zh_numerals_to_arabic("十五岁") == "15岁"
        assert zh_numerals_to_arabic("二十一个") == "21个"

    def test_digit_group_separator_removed(self):
        assert normalize_zh("33,000") == "33000"
        assert normalize_zh("１，２３４，５６７") == "1234567"  # 全角はNFKCでASCII化

    def test_unparseable_number_run_left_untouched(self):
        # 万の重複 (STTハルシネーション、ja.py の「1万万」実例と同型) は
        # クラッシュせず不変換で残る (§5.5「解析不能は触らない」)。
        assert zh_numerals_to_arabic("约1万万年前") == "约1万万年前"
        assert zh_numerals_to_arabic("约1万年前") == "约10000年前"
        assert "万万" in normalize_zh("约1万万年前", strip_all_whitespace_for_cer=True)


# --------------------------------------------------------------------------
# §5.5 対象範囲 0–99,999 (zh.py docstring (c)) — 範囲超過 run は不変換
# --------------------------------------------------------------------------


class TestRangeLimit:
    def test_over_range_runs_left_untouched(self):
        # §5.5 のコンバータ範囲は「integers 0–99,999」。十万(=100,000) 以上は
        # 範囲超過につき不変換で残す (ko.py の _MAX_VALUE と同一の線)。
        assert zh_numerals_to_arabic("十万") == "十万"
        assert zh_numerals_to_arabic("三十万") == "三十万"
        assert zh_numerals_to_arabic("百万") == "百万"
        assert zh_numerals_to_arabic("千万") == "千万"
        assert zh_numerals_to_arabic("10万") == "10万"

    def test_boundary_99999_converts(self):
        # 範囲上限ちょうどは変換される。
        assert zh_numerals_to_arabic("九万九千九百九十九") == "99999"

    def test_idiom_qianwan_negative_left_untouched(self):
        # 慣用句「千万+否定 (くれぐれも〜するな)」— 千万=10^7 が範囲チェックで
        # 自動的に不変換となる (検収レポート再現: 旧実装は 你10000000不要去)。
        assert normalize_zh("你千万不要去") == "你千万不要去"

    def test_approximate_shubaiwan_left_untouched(self):
        # 概数「数百万」— 数 は数詞文字集合外なので run は 百万 のみとなり、
        # 範囲超過で不変換 (検収レポート再現: 旧実装は 数1000000美元)。
        assert normalize_zh("数百万美元") == "数百万美元"

    def test_in_range_composition_still_converts(self):
        # 範囲内の合成は引き続き変換される (範囲チェックの過剰適用がないこと)。
        assert zh_numerals_to_arabic("三万三千") == "33000"
        assert normalize_zh("三万三千") == "33000"


# --------------------------------------------------------------------------
# 裸の位取り文字 run の不変換ガード (zh.py docstring (d))
# --------------------------------------------------------------------------


class TestBareUnitRunGuard:
    def test_bare_unit_chars_left_untouched(self):
        # 係数を持たない裸の位取り文字は不変換 (ko.py の単音節 run ガード相当)。
        for run in ("十", "百", "千", "万"):
            assert zh_numerals_to_arabic(run) == run, f"{run!r} は変換されずに残るべき"

    def test_digit_space_unit_not_merged_fleurs_zh(self):
        # FLEURS zh 参照文の実パターン: ASCII 数字と裸の位取り文字が空白で並ぶ。
        # 検収レポート再現: 旧実装は 万→10000 と変換し、Amendment 1 の全空白
        # 除去後に「不足410000」という存在しない数を合成した。
        assert (
            normalize_zh("人口数量不足 4 万。", strip_all_whitespace_for_cer=True)
            == "人口数量不足4万"
        )
        assert (
            normalize_zh("大约 5 千 人", strip_all_whitespace_for_cer=True)
            == "大约5千人"
        )
        # 凍結版 (空白畳み込みのみ) でも裸の 万 は数値化されない。
        assert normalize_zh("人口数量不足 4 万。") == "人口数量不足 4 万"

    def test_contiguous_coefficient_runs_still_convert(self):
        # 空白なしで係数と結合した run は従来どおり変換される (ガードの過剰
        # 適用がないこと)。
        assert zh_numerals_to_arabic("4万") == "40000"
        assert zh_numerals_to_arabic("五千") == "5000"


# --------------------------------------------------------------------------
# §5.5 あいまいクラスの列挙 — 意図的に変換しない (untouched) ことを保証する
# --------------------------------------------------------------------------


AMBIGUOUS_CLASSES = [
    "一起",   # 「一緒に」— 数とは独立に語彙化
    "一样",   # 「同じ」— 同上
    "一直",   # 「ずっと」— 同上
    "一些",   # 「いくつかの」— 同上
    "一切",   # 「すべて」— 同上
    "一般",   # 「普通の」— 同上
    "一点",   # 「少し」/時刻「1時」— 読みがあいまい
    "一定",   # 「必ず」— 語彙化
    "一共",   # 「合計で」— 語彙化
    "一边",   # 「〜しながら」— 語彙化
    "万一",   # 「もしも」— 慣用句 (run全体一致で個別ブロック)
    "零食",   # 「おやつ」— 零 が「こまごました」の意で語彙化
    "零钱",   # 「小銭」— 同上
    "零售",   # 「小売」— 同上
    "零件",   # 「部品」— 同上
    "十分",   # 「非常に」の副詞 (「10分」の意もあるがあいまいなため不変換)
    "两",     # 単独の两 (量詞前用法: 两个人) — 構造規則で除外
    "三两",   # 重さの単位 liǎng — 同上
    "千万",   # 慣用句「千万不要」/範囲超過 10^7 — 範囲チェック (c) で除外
    "百万",   # 範囲超過 10^6 (概数「数百万」を含む) — 同上
    "十万",   # 範囲超過 100,000 — 同上
    "十",     # 裸の位取り文字 — ガード (d) で除外
    "百",     # 同上
    "千",     # 同上
    "万",     # 同上
]


class TestAmbiguousClasses:
    def test_ambiguous_classes_left_untouched(self):
        for word in AMBIGUOUS_CLASSES:
            assert zh_numerals_to_arabic(word) == word, f"{word!r} は変換されずに残るべき"

    def test_ambiguous_classes_left_untouched_in_context(self):
        # 文中でも同様にあいまいクラスは変換されないことを確認する。
        assert normalize_zh("我们一起去") == "我们一起去"
        assert normalize_zh("和你一样") == "和你一样"
        assert normalize_zh("一般来说") == "一般来说"
        assert normalize_zh("万一下雨") == "万一下雨"
        assert normalize_zh("有一点累") == "有一点累"
        assert normalize_zh("两个人") == "两个人"      # 単位を伴わない两
        assert normalize_zh("三两白酒") == "三两白酒"  # 重さ単位の两
        assert normalize_zh("买零食") == "买零食"
        assert normalize_zh("十分重要") == "十分重要"

    def test_liang_mixed_run_with_trailing_liang_blocked(self):
        # run 内に単位を伴わない 两 が1つでもあれば run 全体を不変換で残す。
        assert zh_numerals_to_arabic("两千两") == "两千两"


# --------------------------------------------------------------------------
# §5.6: OpenCC t2s (繁体→簡体、無条件適用・簡体にはno-op)
# --------------------------------------------------------------------------


class TestTraditionalToSimplified:
    def test_traditional_text_converted_to_simplified(self):
        assert normalize_zh("這是繁體中文") == "这是繁体中文"

    def test_simplified_text_is_noop(self):
        assert normalize_zh("这是简体中文") == "这是简体中文"

    def test_traditional_numerals_converted_then_parsed(self):
        # 萬→万・兩→两 を経由して数詞変換まで到達する (t2s が数値変換より前に
        # 適用されることの確認)。
        assert normalize_zh("兩萬三千") == "23000"
        assert normalize_zh("三萬三千") == "33000"

    def test_traditional_and_simplified_score_identically(self):
        # §5.6 の趣旨: 繁体字出力のエンジンが簡体字リファレンスと公平に比較される。
        assert normalize_zh("我們一起學習") == normalize_zh("我们一起学习")


# --------------------------------------------------------------------------
# §5 手順3: 記号・句読点の除去 (Unicode category P*/S*)
# --------------------------------------------------------------------------


class TestPunctuationRemoval:
    def test_chinese_punctuation_marks(self):
        assert normalize_zh("你好，世界。") == "你好 世界"
        assert normalize_zh("《书名》和“引用”") == "书名 和 引用"
        assert normalize_zh("真的吗？太好了！") == "真的吗 太好了"

    def test_nfkc_fullwidth_latin_and_digits(self):
        assert normalize_zh("ＡＢＣ") == "abc"
        assert normalize_zh("１２３") == "123"


# --------------------------------------------------------------------------
# §5 手順4: 空白 — 凍結版 (畳み込みのみ) vs Amendment 1 (全除去) の二値フラグ
# --------------------------------------------------------------------------


class TestWhitespaceFlag:
    def test_default_keeps_single_spaces(self):
        # 凍結版 (§5.4 字義): 連続空白は単一スペースに畳むが、単一スペースは残す。
        assert normalize_zh("敌对 的 环境") == "敌对 的 环境"
        assert normalize_zh("敌对   的    环境") == "敌对 的 环境"
        assert normalize_zh("  敌对的环境  ") == "敌对的环境"

    def test_strip_all_flag_removes_internal_spaces_too(self):
        # Amendment 1: 分かち書き由来のスペースを全除去し、無スペースの
        # リファレンスとCERで公平に比較できるようにする。
        assert (
            normalize_zh("敌对 的 环境", strip_all_whitespace_for_cer=True)
            == "敌对的环境"
        )
        assert (
            normalize_zh("敌对的环境", strip_all_whitespace_for_cer=True)
            == "敌对的环境"
        )

    def test_both_modes_agree_when_no_internal_spaces(self):
        ref = "今天天气很好"
        assert normalize_zh(ref) == normalize_zh(ref, strip_all_whitespace_for_cer=True)


# --------------------------------------------------------------------------
# Amendment 3: True側の全空白除去は数値変換の**前** (zh.py docstring
# 【処理順 — Amendment 3】参照)
# --------------------------------------------------------------------------


class TestAmendment3WhitespaceBeforeNumbers:
    def test_segmented_numeral_reassembled(self):
        # 再現ケース (修正前 fail): 分かち書きエンジンの数詞断片化。旧実装は
        # 两千/零/二十/六 を独立変換してから空白除去し '20000206' を合成した。
        assert (
            normalize_zh("两千 零 二十 六", strip_all_whitespace_for_cer=True)
            == "2026"
        )

    def test_blocklist_protection_survives_space_removal(self):
        # 再現ケース (修正前 fail): 分かち書きで「万 一」と割れるとブロック
        # リストが効かず 一→1 と変換されていた (旧実装: 万1下雨)。空白除去が
        # 数値変換より前になったので、除去後の「万一」に慣用句ブロックが効く。
        assert (
            normalize_zh("万 一 下 雨", strip_all_whitespace_for_cer=True)
            == "万一下雨"
        )

    def test_boundary_interacts_with_bare_unit_guard(self):
        # ガード (d) との相互作用: 空白除去で数字と直結しても、旧空白境界で
        # 区切った断片「万」が裸の位取り文字である限り run「4万」は変換しない
        # (TestBareUnitRunGuard.test_digit_space_unit_not_merged_fleurs_zh も
        # この経路を通る)。
        assert (
            normalize_zh("总数 4 万 左右", strip_all_whitespace_for_cer=True)
            == "总数4万左右"
        )

    def test_false_side_order_unchanged(self):
        # False側 (凍結字義モード) は処理順不変 — 従来どおり独立変換のまま。
        assert normalize_zh("两千 零 二十 六") == "2000 0 20 6"
        assert normalize_zh("万 一 下 雨") == "万 1 下 雨"


# --------------------------------------------------------------------------
# WERトークナイザ (jieba) / CER文字列
# --------------------------------------------------------------------------


class TestTokenizerAndCerChars:
    def test_tokenize_zh_returns_jieba_tokens(self):
        tokens = tokenize_zh(normalize_zh("今天天气很好"))
        assert tokens == ["今天天气", "很", "好"]

    def test_tokenize_zh_excludes_whitespace_tokens(self):
        # jieba は空白を空白トークンとして返すが、fugashi (ja) と挙動を揃えて
        # 空白のみのトークンは除外する (トークン列に空白が混入しない)。
        spaced = normalize_zh("今天 天气 很 好")
        tokens = tokenize_zh(spaced)
        assert all(tok.strip() for tok in tokens)
        assert tokens == ["今天", "天气", "很", "好"]

    def test_tokenize_zh_after_number_conversion(self):
        tokens = tokenize_zh(normalize_zh("总共三万三千元"))
        assert "33000" in tokens
        assert "元" in tokens

    def test_cer_chars_zh_is_character_sequence(self):
        normalized = normalize_zh("今天天气很好")
        assert cer_chars_zh(normalized) == list(normalized)
        assert "".join(cer_chars_zh(normalized)) == normalized


# --------------------------------------------------------------------------
# べき等性 (2回適用しても結果が変わらない) — 両フラグとも必須
# --------------------------------------------------------------------------


IDEMPOTENCE_SAMPLES = [
    "今天花了三万三千元，买了两千个零件。",
    "敌对 的 环境",
    "第二十次、二零二六年的发布。",
    "万一我们一起迟到，一定十分麻烦。",
    "這是繁體中文的兩萬三千。",
    "ＡＢＣ１２３ 33,000",
]


class TestIdempotence:
    def test_idempotence_default_mode(self):
        for s in IDEMPOTENCE_SAMPLES:
            once = normalize_zh(s)
            twice = normalize_zh(once)
            assert once == twice, f"idempotence failed for {s!r}: {once!r} != {twice!r}"

    def test_idempotence_strip_all_whitespace_mode(self):
        for s in IDEMPOTENCE_SAMPLES:
            once = normalize_zh(s, strip_all_whitespace_for_cer=True)
            twice = normalize_zh(once, strip_all_whitespace_for_cer=True)
            assert once == twice, f"idempotence failed for {s!r}: {once!r} != {twice!r}"
