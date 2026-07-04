"""normalizers/id_.py のテスト — PREREGISTRATION.md §5 (インドネシア語正規化) 準拠確認。

このテストファイルは §5.5 が要求する
「あいまいなクラスは normalizers/<lang>/numbers_test.py 相当のファイルで列挙する」
を満たす、インドネシア語の numbers_test.py 相当も兼ねる
(あいまいクラス列挙は TestAmbiguousClasses を参照)。

モジュール名が id_.py である理由 (Python 組み込み `id()` との衝突回避) は
normalizers/id_.py の docstring 冒頭を参照。
"""

from normalizers.id_ import normalize_id, tokenize_id


class TestNumberEquivalence:
    """§5.5: 綴り数詞→数字、桁区切り除去。"""

    def test_cardinal_composition_with_puluh(self):
        # puluh 合成 (タスク仕様の明記例: dua puluh satu = 21)。
        assert normalize_id("dua puluh satu") == "21"
        assert normalize_id("dua puluh") == "20"
        assert normalize_id("sembilan puluh sembilan") == "99"

    def test_cardinal_teens_with_belas(self):
        assert normalize_id("sepuluh") == "10"
        assert normalize_id("sebelas") == "11"
        assert normalize_id("dua belas") == "12"
        assert normalize_id("sembilan belas") == "19"

    def test_cardinal_hundreds(self):
        assert normalize_id("seratus") == "100"
        assert normalize_id("dua ratus") == "200"
        assert normalize_id("seratus dua puluh") == "120"
        # 標準の読みでは乗数直後の裸の単位桁は一の位 (docstring の線引き参照)。
        assert normalize_id("seratus lima") == "105"

    def test_cardinal_thousands(self):
        # seribu = 1000 (タスク仕様の明記例)。
        assert normalize_id("seribu") == "1000"
        assert normalize_id("dua ribu") == "2000"
        assert normalize_id("seribu lima ratus") == "1500"
        assert normalize_id("tiga puluh tiga ribu") == "33000"
        assert normalize_id("dua ribu lima") == "2005"

    def test_cardinal_range_maximum(self):
        assert (
            normalize_id(
                "sembilan puluh sembilan ribu sembilan ratus sembilan puluh sembilan"
            )
            == "99999"
        )

    def test_equivalence_with_digit_forms(self):
        assert normalize_id("tiga puluh tiga ribu") == normalize_id("33.000") == "33000"
        assert normalize_id("dua puluh satu") == normalize_id("21")

    def test_digit_group_separator_removed(self):
        # id の行: "." = 千区切り (3桁グループ条件つき)。
        assert normalize_id("33.000") == "33000"
        assert normalize_id("1.234.567") == "1234567"

    def test_decimal_comma_becomes_token_boundary(self):
        # "," = 小数点は §5.5 の対象範囲 (整数) 外 → 手順3でトークン境界化
        # (レンジのハイフンと同じ宣言済みノイズクラス)。挙動をピン留めする。
        assert normalize_id("3,5") == "3 5"

    def test_non_grouping_period_becomes_token_boundary(self):
        # 3桁グループを成さないピリオドは桁区切りとみなさない
        # ("3.5" が 35 に化けないことの確認)。
        assert normalize_id("3.5") == "3 5"

    def test_out_of_range_not_converted(self):
        # 0〜99,999 の範囲外は不変換 (seratus ribu = 100000)。
        assert normalize_id("seratus ribu") == "seratus ribu"

    def test_numeric_range_hyphen_becomes_token_boundary(self):
        assert normalize_id("25-30") == "25 30"


class TestAmbiguousClasses:
    """§5.5: あいまいクラスの列挙 — 意図的に変換しない (untouched) ことを保証する。"""

    def test_standalone_cardinals_left_untouched(self):
        # 単独の基数語は不変換 (乗数語必須の保守線; 慣用表現を守る)。
        for word in ["satu", "dua", "tiga", "lima", "sembilan"]:
            assert normalize_id(word) == word, f"{word!r} は変換されずに残るべき"

    def test_standalone_cardinals_left_untouched_in_context(self):
        assert normalize_id("salah satu dari mereka") == "salah satu dari mereka"
        # satu-satunya はハイフンが境界化した後も単独基数語の連続なので不変換。
        assert normalize_id("satu-satunya") == "satu satunya"

    def test_counting_sequence_left_untouched(self):
        # 数え上げ列は乗数語を含まないため不変換。
        assert normalize_id("satu dua tiga") == "satu dua tiga"

    def test_ordinals_left_untouched(self):
        # pertama (補充形) / kedua (「両方の」と同形) / ketiga … は全て不変換。
        assert normalize_id("pertama") == "pertama"
        assert normalize_id("kedua") == "kedua"
        assert normalize_id("ketiga") == "ketiga"
        assert normalize_id("kedua orang itu") == "kedua orang itu"
        # ke-2 はハイフンが手順3で境界化する (宣言済みノイズ、挙動のピン留め)。
        assert normalize_id("ke-2") == "ke 2"

    def test_se_prefix_words_left_untouched(self):
        # se- 接頭辞語で数詞と認めるのは sepuluh/sebelas/seratus/seribu の
        # 完全一致4形のみ。一般の se- 語は数詞扱いしない。
        assert normalize_id("sebentar") == "sebentar"
        assert normalize_id("sekolah") == "sekolah"
        assert normalize_id("sekali lagi") == "sekali lagi"

    def test_zero_words_left_untouched(self):
        # nol / kosong は語彙外 (docstring「ゼロの扱い」参照)。
        assert normalize_id("nol") == "nol"
        assert normalize_id("kosong") == "kosong"

    def test_bare_multiplier_left_untouched(self):
        # 係数なしの ratus/ribu は不変換。
        assert normalize_id("ratus") == "ratus"
        assert normalize_id("beberapa ribu orang") == "beberapa ribu orang"

    def test_nonstandard_forms_left_untouched(self):
        # 標準形は sepuluh/sebelas。非標準の satu puluh / satu belas は
        # パース失敗 → run 全体が不変換 (全か無か)。
        assert normalize_id("satu puluh") == "satu puluh"
        assert normalize_id("satu belas") == "satu belas"
        assert normalize_id("dua seribu") == "dua seribu"

    def test_ascii_digit_not_merged_with_spelled_multiplier(self):
        # ASCII 数字と綴り乗数語は結合しない (ribu 単独 run はパース失敗)。
        assert normalize_id("20 ribu") == "20 ribu"


class TestPunctuationCaseNFKC:
    """§5 手順1-3: NFKC、ケースフォールド、記号除去 (語中アポストロフィ例外)。"""

    def test_punctuation_removed(self):
        assert normalize_id("Selamat pagi, dunia!") == "selamat pagi dunia"
        assert normalize_id("Benarkah...?") == "benarkah"

    def test_case_folding(self):
        assert normalize_id("INDONESIA Raya") == "indonesia raya"
        assert normalize_id("Jakarta") == normalize_id("JAKARTA")

    def test_nfkc_fullwidth_latin(self):
        assert normalize_id("ＡＢＣ１２３") == "abc123"

    def test_word_internal_apostrophe_kept(self):
        # id はラテン文字言語なので §5 手順3の例外が適用される
        # (Jum'at のような綴りが実在する)。
        assert normalize_id("Jum'at") == "jum'at"
        assert normalize_id("Jum’at") == "jum'at"  # ’→' 標準化

    def test_leading_apostrophe_removed(self):
        assert normalize_id("'selamat") == "selamat"


class TestWhitespace:
    """§5 手順4: 空白畳み込み。"""

    def test_whitespace_runs_collapsed_and_stripped(self):
        assert normalize_id("selamat   pagi") == "selamat pagi"
        assert normalize_id("  selamat pagi  ") == "selamat pagi"
        assert normalize_id("selamat\tpagi\nsemua") == "selamat pagi semua"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "dua puluh satu orang",
        "seribu lima ratus rupiah",
        "tiga puluh tiga ribu",
        "33.000",
        "3,5",
        "salah satu dari kedua orang itu",
        "Selamat pagi, dunia! Jum'at",
        "beberapa ribu orang",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_id(sample)
            twice = normalize_id(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizeId:
    """§5.6 (id): 空白分割 WER トークナイザ。"""

    def test_whitespace_split(self):
        assert tokenize_id("Selamat pagi, dunia!") == ["selamat", "pagi", "dunia"]

    def test_number_converted_before_split(self):
        assert tokenize_id("dua puluh satu orang") == ["21", "orang"]

    def test_empty_string(self):
        assert tokenize_id("") == []
        assert tokenize_id("   ") == []

    def test_matches_normalize_id_split(self):
        text = "Saya membayar 33.000 rupiah untuk dua puluh satu telur."
        assert tokenize_id(text) == normalize_id(text).split(" ")
