"""
normalizers/es.py のテスト (PREREGISTRATION §5 準拠確認)。

§5.5 の数値等価クラス (基数・序数・桁区切り・小数)、曖昧クラスの不変換、
記号/ケース/NFKC、冪等性、tokenize を最低限カバーする (test_en.py と同様式)。
"""
from normalizers.es import normalize_es, tokenize_es


class TestNumberEquivalence:
    """§5.5: 数値等価クラス (スペイン語)。"""

    def test_spelled_cardinal_equals_digit(self):
        assert normalize_es("setenta y ocho") == normalize_es("78")
        assert normalize_es("setenta y ocho") == "78"
        assert normalize_es("veintiuno") == "21"
        assert normalize_es("veintiún") == "21"
        assert normalize_es("dieciséis") == "16"
        assert normalize_es("cero") == "0"

    def test_y_composition(self):
        # "y" は <10の位> y <1の位> の形でのみ数詞列として消費される。
        assert normalize_es("treinta y uno") == "31"
        assert normalize_es("cuarenta y cinco") == "45"

    def test_hundreds_and_thousands(self):
        assert normalize_es("ciento cinco") == "105"
        assert normalize_es("cien") == "100"
        assert normalize_es("mil") == "1000"
        assert normalize_es("doscientos treinta y cuatro") == "234"
        assert normalize_es("quinientas") == "500"
        assert normalize_es("treinta y tres mil") == normalize_es("33.000")
        assert normalize_es("treinta y tres mil") == "33000"
        assert normalize_es("treinta y tres mil quinientos") == "33500"

    def test_un_participates_in_ciento_mil_remainder(self):
        # ciento/mil の余り位置は数詞列の内部 → un/una は数詞として参加する
        # (101/1001 の標準形。検収で確定したバグの修正)。
        assert normalize_es("ciento un libros") == "101 libros"
        assert normalize_es("ciento una") == "101"
        assert normalize_es("mil un libros") == "1001 libros"

    def test_out_of_range_run_left_untouched_atomically(self):
        # §5.5 範囲超過 (>99,999) は run 全体を不変換 — "100 1000" のような
        # 部分変換に割らない (検収で確定したバグの修正)。
        assert normalize_es("cien mil") == "cien mil"
        assert normalize_es("doscientos mil") == "doscientos mil"
        assert normalize_es("doscientos mil quinientos") == "doscientos mil quinientos"

    def test_range_boundary_99999_still_converts(self):
        assert (
            normalize_es("noventa y nueve mil novecientos noventa y nueve")
            == "99999"
        )
        assert normalize_es("noventa y nueve mil") == "99000"

    def test_spelled_ordinal_ends_as_bare_digit(self):
        # §5.5: 序数の最終形は裸の数字 (en: twentieth→20th→20 と同じ扱い)。
        assert normalize_es("el primero") == "el 1"
        assert normalize_es("primera") == "1"
        assert normalize_es("tercero") == "3"
        assert normalize_es("décimo") == "10"
        assert normalize_es("vigésimo primero") == "21"
        assert normalize_es("el vigésimo siglo") == normalize_es("el 20º siglo")

    def test_digit_ordinal_suffix_stripped(self):
        # NFKC が º→o / ª→a に変換した序数標識を最後に剥がす。
        assert normalize_es("20º") == "20"
        assert normalize_es("20ª") == "20"
        assert normalize_es("1º") == "1"

    def test_digit_group_separator_removed(self):
        # スペイン語の千区切りは "." (§5.5 の言語別慣習行)。
        assert normalize_es("33.000") == normalize_es("33000")
        assert normalize_es("33.000") == "33000"
        assert normalize_es("1.234.567") == "1234567"

    def test_decimal_comma_normalized_to_dot_one_token(self):
        # スペイン語の小数点は ","。"." に正規化して1トークンに保つ
        # (モジュールdocstringに明記した本実装の決定)。
        assert normalize_es("3,14") == "3.14"
        assert tokenize_es("3,14") == ["3.14"]
        assert normalize_es("33.000,50") == "33000.50"

    def test_non_separator_dot_not_merged(self):
        assert normalize_es("3.14") == "3.14"

    def test_numeric_range_hyphen_becomes_token_boundary(self):
        # §5.5: レンジのハイフンは句読点除去でトークン境界になる。
        assert normalize_es("25-30") == "25 30"
        assert tokenize_es("25-30") == ["25", "30"]


class TestAmbiguousClassesLeftUntouched:
    """§5.5: 曖昧クラスは変換しない (冠詞/数詞の文脈判定をしない)。"""

    def test_un_una_article_untouched(self):
        assert normalize_es("un libro") == "un libro"
        assert normalize_es("una casa") == "una casa"
        assert normalize_es("un") == "un"
        assert normalize_es("una") == "una"

    def test_un_converts_inside_number_sequence(self):
        # 数詞列の内部では un/una は数詞としてのみ現れるため変換に参加する。
        assert normalize_es("treinta y un") == "31"
        assert normalize_es("treinta y una") == "31"

    def test_uno_converts_standalone(self):
        # 冠詞は "un" であって "uno" ではないため、uno は数詞として変換する
        # (モジュールdocstringに明記した決定論的選択)。
        assert normalize_es("uno") == "1"

    def test_segundo_cuarto_homographs_untouched(self):
        # segundo (秒)・cuarto (部屋) の同形異義 → 変換しない。
        assert normalize_es("un segundo") == "un segundo"
        assert normalize_es("segunda") == "segunda"
        assert normalize_es("el cuarto") == "el cuarto"
        assert normalize_es("cuarta") == "cuarta"

    def test_ordinal_tens_plus_ambiguous_unit_untouched_atomically(self):
        # 序数10の位 + 曖昧クラス序数語は run 全体を不変換 (全か無か)。
        # 旧挙動の "10 cuarto" 型混合出力 (部分変換) は禁止 (検収F8の修正)。
        assert normalize_es("décimo cuarto") == "décimo cuarto"
        assert normalize_es("décimo segundo") == "décimo segundo"
        assert normalize_es("vigésimo segundo") == "vigésimo segundo"
        # 無曖昧な序数合成は引き続き変換される。
        assert normalize_es("décimo quinto") == "15"
        assert normalize_es("vigésimo primero") == "21"

    def test_conjunction_y_not_merged(self):
        # 1の位どうしの "y" は数詞列ではない ("cinco y seis" = 5 と 6)。
        assert normalize_es("cinco y seis") == "5 y 6"


class TestCaseFoldingAndPunctuation:
    def test_case_folding(self):
        assert normalize_es("Hola MUNDO") == normalize_es("hola mundo")
        assert normalize_es("HOLA") == "hola"

    def test_diacritics_kept(self):
        # remove_diacritics=False (デフォルト): ñ やアクセントは保持される
        # (año と ano は別語)。
        assert normalize_es("año") == "año"
        assert "é" in normalize_es("café")

    def test_punctuation_removed_including_inverted_marks(self):
        assert normalize_es("¿Qué? ¡Hola!") == "qué hola"
        assert normalize_es("Hola, mundo.") == "hola mundo"

    def test_curly_apostrophe_standardized(self):
        assert normalize_es("O’Brien") == normalize_es("O'Brien")

    def test_nfkc(self):
        assert normalize_es("２１") == "21"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "veintiuno",
        "treinta y uno",
        "treinta y tres mil quinientos",
        "33.000",
        "3,14",
        "33.000,50",
        "un libro",
        "un segundo",
        "vigésimo primero",
        "20º",
        "¿Qué? ¡Hola!",
        "año",
        "cinco y seis",
        "25-30",
        "1,000",  # 宣言済み衝突クラス: 1パス目で "1000" に確定し以後不動
        # 範囲超過の原子的ガード・余り位置の un・曖昧序数複合ガード:
        "cien mil",
        "doscientos mil",
        "ciento un libros",
        "mil un libros",
        "décimo cuarto",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_es(sample)
            twice = normalize_es(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizeEs:
    def test_whitespace_split(self):
        assert tokenize_es("¡Hola, mundo!") == ["hola", "mundo"]

    def test_empty_string(self):
        assert tokenize_es("") == []
        assert tokenize_es("   ") == []

    def test_matches_normalize_es_split(self):
        text = "La tienda tenía 25-30 artículos por 33.000 euros."
        assert tokenize_es(text) == normalize_es(text).split(" ")
