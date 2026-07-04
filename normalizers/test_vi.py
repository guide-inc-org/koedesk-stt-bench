"""normalizers/vi.py のテスト — PREREGISTRATION.md §5 (ベトナム語正規化) 準拠確認。

このテストファイルは §5.5 が要求する
「あいまいなクラスは normalizers/<lang>/numbers_test.py 相当のファイルで列挙する」
を満たす、ベトナム語の numbers_test.py 相当も兼ねる
(あいまいクラス列挙は TestAmbiguousClasses を参照)。
"""

from normalizers.vi import normalize_vi, tokenize_vi


class TestNumberEquivalence:
    """§5.5: 綴り数詞→数字、桁区切り除去。"""

    def test_cardinal_composition_with_muoi(self):
        # mươi 合成 (タスク仕様の明記例: hai mươi mốt = 21)。
        assert normalize_vi("hai mươi mốt") == "21"
        assert normalize_vi("hai mươi") == "20"
        assert normalize_vi("hai mươi tư") == "24"
        assert normalize_vi("năm mươi") == "50"
        assert normalize_vi("chín mươi chín") == "99"

    def test_cardinal_teens_with_muoi10(self):
        assert normalize_vi("mười") == "10"
        assert normalize_vi("mười một") == "11"
        assert normalize_vi("mười lăm") == "15"
        assert normalize_vi("mười chín") == "19"

    def test_cardinal_hundreds_with_linh_le(self):
        # linh/lẻ (タスク仕様の明記例: một trăm linh năm = 105)。
        assert normalize_vi("một trăm linh năm") == "105"
        assert normalize_vi("một trăm lẻ năm") == "105"
        assert normalize_vi("một trăm") == "100"
        assert normalize_vi("ba trăm hai mươi mốt") == "321"

    def test_cardinal_thousands_nghin_ngan(self):
        assert normalize_vi("hai nghìn") == "2000"
        assert normalize_vi("hai ngàn") == "2000"  # 南部形 ngàn も同値
        assert normalize_vi("ba mươi ba nghìn") == "33000"
        assert normalize_vi("hai nghìn lẻ năm") == "2005"
        # 年号型の読み (không = trăm の係数 0)。
        assert normalize_vi("hai nghìn không trăm hai mươi sáu") == "2026"

    def test_leading_nam_backoff(self):
        # 決定論的バックオフ (検収で確定した欠落の修正): run 先頭の năm (年) を
        # 1個外して再パースし、"năm 2026" の読み下しを変換する。
        assert (
            normalize_vi("năm hai nghìn không trăm hai mươi sáu") == "năm 2026"
        )
        assert normalize_vi("năm hai nghìn") == "năm 2000"
        # năm が係数として正しくパースできる run はバックオフしない。
        assert normalize_vi("năm mươi") == "50"
        assert normalize_vi("năm nghìn") == "5000"

    def test_cardinal_van(self):
        assert normalize_vi("một vạn") == "10000"
        assert normalize_vi("hai vạn") == "20000"

    def test_equivalence_with_digit_forms(self):
        assert normalize_vi("ba mươi ba nghìn") == normalize_vi("33.000") == "33000"
        assert normalize_vi("hai mươi mốt") == normalize_vi("21")

    def test_digit_group_separator_removed(self):
        # vi の行: "." = 千区切り (3桁グループ条件つき)。
        assert normalize_vi("33.000") == "33000"
        assert normalize_vi("1.234.567") == "1234567"

    def test_decimal_comma_becomes_token_boundary(self):
        # "," = 小数点は §5.5 の対象範囲 (整数) 外 → 手順3でトークン境界化
        # (レンジのハイフンと同じ宣言済みノイズクラス)。挙動をピン留めする。
        assert normalize_vi("3,5") == "3 5"

    def test_non_grouping_period_becomes_token_boundary(self):
        # 3桁グループを成さないピリオドは桁区切りとみなさない (案B、
        # docstring 参照)。"3.5" が 35 に化けないことの確認。
        assert normalize_vi("3.5") == "3 5"

    def test_out_of_range_not_converted(self):
        # 0〜99,999 の範囲外は不変換 (một trăm nghìn = 100000)。
        assert normalize_vi("một trăm nghìn") == "một trăm nghìn"

    def test_numeric_range_hyphen_becomes_token_boundary(self):
        assert normalize_vi("25-30") == "25 30"


class TestAmbiguousClasses:
    """§5.5: あいまいクラスの列挙 — 意図的に変換しない (untouched) ことを保証する。"""

    # 単独の基数語: 非数詞の同綴り異義が支配的 (乗数語必須の構造規則で除外)。
    STANDALONE_CARDINALS = [
        "một",    # 冠詞的用法 (một chút = 少し)
        "năm",    # 年
        "ba",     # 父
        "tư",     # 私的 / 第4
        "chín",   # 熟した
        "không",  # 否定辞
    ]

    def test_standalone_cardinals_left_untouched(self):
        for word in self.STANDALONE_CARDINALS:
            assert normalize_vi(word) == word, f"{word!r} は変換されずに残るべき"

    def test_standalone_cardinals_left_untouched_in_context(self):
        assert normalize_vi("một ngày đẹp trời") == "một ngày đẹp trời"
        assert normalize_vi("tôi không biết") == "tôi không biết"

    def test_counting_sequence_left_untouched(self):
        # 数え上げ列は乗数語を含まないため不変換。
        assert normalize_vi("một hai ba") == "một hai ba"

    def test_nam_after_muoi_is_years_not_five(self):
        # mười năm = 10年 / hai mươi năm = 20年 (năm=年)。15/25 は lăm のみ。
        # 先頭 năm バックオフは run 先頭にのみ働き、これらの宣言済み挙動
        # (run 先頭は hai/mười) を変えない。
        assert normalize_vi("mười năm") == "mười năm"
        assert normalize_vi("hai mươi năm") == "hai mươi năm"

    def test_bare_trailing_digit_after_scale_left_untouched(self):
        # 乗数語直後の裸の単位桁は linh/lẻ 必須の線引きで不変換
        # (hai nghìn năm = 「2000年」の読みを守る)。
        assert normalize_vi("hai nghìn năm") == "hai nghìn năm"
        assert normalize_vi("hai trăm ba") == "hai trăm ba"

    def test_ordinals_left_untouched_weekday_homographs(self):
        # thứ hai(月曜)〜thứ bảy(土曜) が曜日名と完全同形のため、序数は全て不変換。
        assert normalize_vi("thứ hai") == "thứ hai"
        assert normalize_vi("thứ ba") == "thứ ba"
        assert normalize_vi("thứ nhất") == "thứ nhất"
        assert normalize_vi("ngày thứ tư") == "ngày thứ tư"

    def test_bare_multiplier_left_untouched(self):
        # 係数なしの乗数語は不変換 (hàng nghìn = 「何千もの」等)。
        assert normalize_vi("hàng nghìn người") == "hàng nghìn người"
        assert normalize_vi("trăm năm") == "trăm năm"
        assert normalize_vi("vạn vật") == "vạn vật"

    def test_nonstandard_forms_left_untouched(self):
        # 標準文法外の並びはパース失敗 → run 全体が不変換 (全か無か)。
        assert normalize_vi("một mươi") == "một mươi"
        assert normalize_vi("mười mươi") == "mười mươi"

    def test_ascii_digit_not_merged_with_spelled_multiplier(self):
        # ASCII 数字と綴り乗数語は結合しない (nghìn 単独 run はパース失敗)。
        assert normalize_vi("20 nghìn") == "20 nghìn"


class TestPunctuationCaseNFKC:
    """§5 手順1-3: NFKC、ケースフォールド、記号除去 (語中アポストロフィ例外)。"""

    def test_punctuation_removed(self):
        assert normalize_vi("Xin chào, thế giới!") == "xin chào thế giới"
        assert normalize_vi("Thật sao...?") == "thật sao"

    def test_case_folding_with_diacritics(self):
        assert normalize_vi("VIỆT NAM") == "việt nam"
        assert normalize_vi("Hà Nội") == "hà nội"

    def test_nfkc_composes_decomposed_input(self):
        # NFD (分解済み) 入力も NFKC の正準合成で合成済み形と同値になる
        # (エンジンによって合成形/分解形が揺れても数詞語彙と一致する)。
        import unicodedata

        decomposed = unicodedata.normalize("NFD", "tiếng Việt")
        assert decomposed != "tiếng Việt"  # 前提: 分解形は合成形と異なる
        assert normalize_vi(decomposed) == normalize_vi("tiếng Việt") == "tiếng việt"
        # 数詞も分解形から正しく変換される。
        assert normalize_vi(unicodedata.normalize("NFD", "hai mươi mốt")) == "21"

    def test_nfkc_fullwidth_latin(self):
        assert normalize_vi("ＡＢＣ１２３") == "abc123"

    def test_word_internal_apostrophe_kept(self):
        # vi はラテン文字言語なので §5 手順3の例外が適用される。
        assert normalize_vi("don't") == "don't"
        assert normalize_vi("don’t") == "don't"  # ’→' 標準化

    def test_leading_apostrophe_removed(self):
        assert normalize_vi("'xin chào") == "xin chào"


class TestWhitespace:
    """§5 手順4: 空白畳み込み。"""

    def test_whitespace_runs_collapsed_and_stripped(self):
        assert normalize_vi("xin   chào") == "xin chào"
        assert normalize_vi("  xin chào  ") == "xin chào"
        assert normalize_vi("xin\tchào\nbạn") == "xin chào bạn"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "hai mươi mốt người",
        "một trăm linh năm",
        "ba mươi ba nghìn đồng",
        "hai nghìn không trăm hai mươi sáu",
        "năm hai nghìn không trăm hai mươi sáu",  # 先頭 năm バックオフ
        "33.000",
        "3,5",
        "mười năm trước, thứ hai tuần sau",
        "Xin chào, thế giới! don't",
        "hàng nghìn người",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_vi(sample)
            twice = normalize_vi(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizeVi:
    """§5.6 (vi): 空白分割 WER トークナイザ。"""

    def test_whitespace_split(self):
        assert tokenize_vi("Xin chào, thế giới!") == ["xin", "chào", "thế", "giới"]

    def test_number_converted_before_split(self):
        assert tokenize_vi("hai mươi mốt người") == ["21", "người"]

    def test_empty_string(self):
        assert tokenize_vi("") == []
        assert tokenize_vi("   ") == []

    def test_matches_normalize_vi_split(self):
        text = "Tôi đã trả 33.000 đồng cho hai mươi mốt quả trứng."
        assert tokenize_vi(text) == normalize_vi(text).split(" ")
