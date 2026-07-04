"""
normalizers/de.py のテスト (PREREGISTRATION §5 準拠確認)。

§5.5 の数値等価クラス (基数・序数・桁区切り・小数)、曖昧クラスの不変換、
記号/ケース/NFKC、冪等性、tokenize を最低限カバーする (test_en.py と同様式)。
"""
from normalizers.de import normalize_de, tokenize_de


class TestNumberEquivalence:
    """§5.5: 数値等価クラス (ドイツ語)。"""

    def test_spelled_cardinal_equals_digit(self):
        # 逆順合成 (einundzwanzig = 1+und+20 = 21)
        assert normalize_de("einundzwanzig") == normalize_de("21")
        assert normalize_de("einundzwanzig") == "21"
        assert normalize_de("achtundsiebzig") == "78"

    def test_compound_cardinal_with_scale_words(self):
        assert normalize_de("dreihundertfünfundvierzig") == "345"
        assert normalize_de("dreiunddreißigtausend") == normalize_de("33.000")
        assert normalize_de("dreiunddreißigtausend") == "33000"
        assert normalize_de("zweitausendsechsundzwanzig") == "2026"
        assert normalize_de("hundert") == "100"
        assert normalize_de("tausend") == "1000"
        assert normalize_de("eins") == "1"

    def test_out_of_range_left_untouched(self):
        # §5.5 のスコープは 0-99,999。超える複合語は変換しない。
        assert normalize_de("dreihunderttausend") == "dreihunderttausend"

    def test_year_style_hundert_coefficient(self):
        # hundert の係数に 10-99 (年号型の読み) を許可する
        # (検収で確定した欠落の修正。1100-1999 の年号の標準形)。
        assert normalize_de("achtzehnhundert") == "1800"
        assert normalize_de("neunzehnhundertvierundachtzig") == "1984"
        assert normalize_de("dreizehnhundert") == "1300"  # teens 係数
        assert normalize_de("im Jahr neunzehnhundertneunundneunzig") == "im jahr 1999"

    def test_year_style_hundert_does_not_break_sweep_targets(self):
        # 誤変換スイープ対象 (非数詞語) が無傷であることの維持テスト。
        assert normalize_de("Jahrhundert") == "jahrhundert"
        assert normalize_de("Jahrtausend") == "jahrtausend"
        assert normalize_de("die achtziger Jahre") == "die achtziger jahre"
        assert normalize_de("nullhundert") == "nullhundert"  # 係数0は数詞でない

    def test_spelled_ordinal_ends_as_bare_digit(self):
        # §5.5: 序数の最終形は裸の数字 (en: twentieth→20th→20 と同じ扱い)。
        assert normalize_de("der dritte Mann") == "der 3 mann"
        assert normalize_de("am zwanzigsten") == "am 20"
        assert normalize_de("die erste") == "die 1"
        assert normalize_de("das einundzwanzigste Jahrhundert") == "das 21 jahrhundert"
        assert normalize_de("hundertdritte") == "103"

    def test_digit_group_separator_removed(self):
        # ドイツ語の千区切りは "." (§5.5 の言語別慣習行)。
        assert normalize_de("33.000") == normalize_de("33000")
        assert normalize_de("33.000") == "33000"
        assert normalize_de("1.234.567") == "1234567"
        # スイス式 "'" 千区切りも同一規則で除去する。
        assert normalize_de("33'000") == "33000"

    def test_decimal_comma_normalized_to_dot_one_token(self):
        # ドイツ語の小数点は ","。"." に正規化して1トークンに保つ
        # (モジュールdocstringに明記した本実装の決定)。
        assert normalize_de("3,14") == "3.14"
        assert tokenize_de("3,14") == ["3.14"]
        assert normalize_de("33.000,50") == "33000.50"

    def test_non_separator_dot_not_merged(self):
        # 「直後がちょうど3桁」でない "." は千区切りとして扱わない。
        assert normalize_de("3.14") == "3.14"

    def test_numeric_range_hyphen_becomes_token_boundary(self):
        # §5.5: レンジのハイフンは句読点除去でトークン境界になる。
        assert normalize_de("25-30") == "25 30"
        assert tokenize_de("25-30") == ["25", "30"]


class TestAmbiguousClassesLeftUntouched:
    """§5.5: 曖昧クラスは変換しない (冠詞/数詞の文脈判定をしない)。"""

    def test_ein_article_untouched(self):
        assert normalize_de("ein Haus") == "ein haus"
        assert normalize_de("eine Katze") == "eine katze"
        assert normalize_de("einen Moment") == "einen moment"
        assert normalize_de("einer Frau") == "einer frau"
        assert normalize_de("einem Kind") == "einem kind"
        assert normalize_de("eines Tages") == "eines tages"

    def test_ein_converts_inside_compounds(self):
        # 複合語の構成要素としての ein は数詞 (曖昧性がない)。
        assert normalize_de("einhundert") == "100"
        assert normalize_de("eintausend") == "1000"
        assert normalize_de("einundzwanzig") == "21"

    def test_achte_achten_verb_homograph_untouched(self):
        # achten (尊重する) の活用形と序数8の変化形が同形 → ブロックリスト。
        assert normalize_de("wir achten darauf") == "wir achten darauf"
        assert normalize_de("ich achte darauf") == "ich achte darauf"

    def test_acht_cardinal_still_converts(self):
        # 基数 acht と非ブロック序数変化形は変換する (意図した非対称)。
        assert normalize_de("acht") == "8"
        assert normalize_de("achter") == "8"


class TestCaseFoldingAndPunctuation:
    def test_case_folding_and_sharp_s(self):
        # casefold は ß→ss を行う (両表記が同値になる)。
        assert normalize_de("Größe") == normalize_de("GRÖSSE")
        assert normalize_de("Größe") == "grösse"

    def test_diacritics_kept(self):
        # remove_diacritics=False (デフォルト): ウムラウトは保持される。
        assert normalize_de("für") == "für"
        assert "ü" in normalize_de("Über München")

    def test_punctuation_removed(self):
        assert normalize_de("Hallo, Welt!") == "hallo welt"
        assert normalize_de("Was... ist das?") == "was ist das"

    def test_word_internal_apostrophe_kept(self):
        # §5 ステップ3の明示例外 (’→' 標準化を含む)。
        assert normalize_de("geht's") == "geht's"
        assert normalize_de("geht’s") == normalize_de("geht's")

    def test_nfkc(self):
        # 全角英数字は NFKC で ASCII に揃う。
        assert normalize_de("２１") == "21"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "einundzwanzig",
        "dreiunddreißigtausend",
        "33.000",
        "33'000",
        "3,14",
        "33.000,50",
        "der dritte Mann",
        "ein Haus",
        "wir achten darauf",
        "Größe",
        "geht's",
        "25-30",
        "Hallo, Welt!",
        "1,000",  # 宣言済み衝突クラス: 1パス目で "1000" に確定し以後不動
        "neunzehnhundertvierundachtzig",  # 年号型 hundert
        "Jahrhundert",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_de(sample)
            twice = normalize_de(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizeDe:
    def test_whitespace_split(self):
        assert tokenize_de("Hallo, Welt!") == ["hallo", "welt"]

    def test_empty_string(self):
        assert tokenize_de("") == []
        assert tokenize_de("   ") == []

    def test_matches_normalize_de_split(self):
        text = "Der Laden hatte 25-30 Artikel für 33.000 Euro."
        assert tokenize_de(text) == normalize_de(text).split(" ")
