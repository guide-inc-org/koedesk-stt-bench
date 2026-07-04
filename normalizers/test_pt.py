"""
normalizers/pt.py のテスト (PREREGISTRATION §5 準拠確認)。

§5.5 の数値等価クラス (基数・序数・桁区切り・小数)、曖昧クラスの不変換、
記号/ケース/NFKC、冪等性、tokenize を最低限カバーする (test_en.py と同様式)。
"""
from normalizers.pt import normalize_pt, tokenize_pt


class TestNumberEquivalence:
    """§5.5: 数値等価クラス (ポルトガル語)。"""

    def test_spelled_cardinal_equals_digit(self):
        assert normalize_pt("setenta e oito") == normalize_pt("78")
        assert normalize_pt("setenta e oito") == "78"
        assert normalize_pt("vinte e um") == "21"
        assert normalize_pt("três") == "3"
        assert normalize_pt("duas") == "2"
        assert normalize_pt("zero") == "0"

    def test_teens_brazilian_and_european_variants(self):
        assert normalize_pt("dezesseis") == "16"
        assert normalize_pt("dezasseis") == "16"
        assert normalize_pt("catorze") == normalize_pt("quatorze")
        assert normalize_pt("catorze") == "14"

    def test_hundreds_and_thousands(self):
        assert normalize_pt("cem") == "100"
        assert normalize_pt("cento e vinte e três") == "123"
        assert normalize_pt("duzentos e trinta") == "230"
        assert normalize_pt("mil") == "1000"
        assert normalize_pt("mil e quinhentos") == "1500"
        assert normalize_pt("trinta e três mil") == normalize_pt("33.000")
        assert normalize_pt("trinta e três mil") == "33000"
        assert normalize_pt("trinta e três mil e quinhentos") == "33500"
        assert normalize_pt("mil novecentos e oitenta e quatro") == "1984"

    def test_um_participates_in_cento_mil_remainder(self):
        # cento/mil の余り位置は数詞列の内部 → um/uma は数詞として参加する
        # (101/1001 の標準形。検収で確定したバグの修正)。
        assert normalize_pt("cento e um") == "101"
        assert normalize_pt("cento e uma") == "101"
        assert normalize_pt("mil e um") == "1001"
        assert normalize_pt("duzentos e um livros") == "201 livros"

    def test_out_of_range_run_left_untouched_atomically(self):
        # §5.5 範囲超過 (>99,999) は run 全体を不変換 — "100 1000" のような
        # 部分変換に割らない (検収で確定したバグの修正)。
        assert normalize_pt("cem mil") == "cem mil"
        assert normalize_pt("duzentos mil") == "duzentos mil"
        assert normalize_pt("duzentos mil e quinhentos") == "duzentos mil e quinhentos"

    def test_range_boundary_99999_still_converts(self):
        assert (
            normalize_pt("noventa e nove mil novecentos e noventa e nove")
            == "99999"
        )
        assert normalize_pt("noventa e nove mil") == "99000"

    def test_spelled_ordinal_ends_as_bare_digit(self):
        # §5.5: 序数の最終形は裸の数字 (en: twentieth→20th→20 と同じ扱い)。
        assert normalize_pt("o primeiro") == "o 1"
        assert normalize_pt("primeira") == "1"
        assert normalize_pt("terceiro") == "3"
        assert normalize_pt("décimo") == "10"
        assert normalize_pt("décimo primeiro") == "11"
        assert normalize_pt("o vigésimo século") == normalize_pt("o 20º século")

    def test_digit_ordinal_suffix_stripped(self):
        # NFKC が º→o / ª→a に変換した序数標識を最後に剥がす。
        assert normalize_pt("20º") == "20"
        assert normalize_pt("20ª") == "20"
        assert normalize_pt("1º") == "1"

    def test_digit_group_separator_removed(self):
        # ポルトガル語の千区切りは "." (§5.5 の言語別慣習行)。
        assert normalize_pt("33.000") == normalize_pt("33000")
        assert normalize_pt("33.000") == "33000"
        assert normalize_pt("1.234.567") == "1234567"

    def test_decimal_comma_normalized_to_dot_one_token(self):
        # ポルトガル語の小数点は ","。"." に正規化して1トークンに保つ
        # (モジュールdocstringに明記した本実装の決定)。
        assert normalize_pt("3,14") == "3.14"
        assert tokenize_pt("3,14") == ["3.14"]
        assert normalize_pt("33.000,50") == "33000.50"

    def test_non_separator_dot_not_merged(self):
        assert normalize_pt("3.14") == "3.14"

    def test_numeric_range_hyphen_becomes_token_boundary(self):
        # §5.5: レンジのハイフンは句読点除去でトークン境界になる。
        assert normalize_pt("25-30") == "25 30"
        assert tokenize_pt("25-30") == ["25", "30"]


class TestAmbiguousClassesLeftUntouched:
    """§5.5: 曖昧クラスは変換しない (冠詞・曜日等との文脈判定をしない)。"""

    def test_um_uma_article_untouched(self):
        # ポルトガル語は冠詞と数詞1が完全同形 → 単独では変換しない。
        assert normalize_pt("um livro") == "um livro"
        assert normalize_pt("uma casa") == "uma casa"
        assert normalize_pt("um") == "um"
        assert normalize_pt("uma") == "uma"

    def test_um_converts_inside_number_sequence(self):
        # 数詞列の内部では um/uma は数詞としてのみ現れるため変換に参加する。
        assert normalize_pt("vinte e um") == "21"
        assert normalize_pt("trinta e uma") == "31"

    def test_weekday_and_noun_homographs_untouched(self):
        # segunda/quarta/quinta/sexta (曜日)・segundo (秒/〜によれば)・
        # quarto (部屋) の同形異義 → 変換しない。
        assert normalize_pt("um segundo") == "um segundo"
        assert normalize_pt("segunda") == "segunda"
        assert normalize_pt("o quarto") == "o quarto"
        assert normalize_pt("quarta") == "quarta"
        assert normalize_pt("quinta") == "quinta"
        assert normalize_pt("sexta") == "sexta"

    def test_masculine_ordinals_still_convert(self):
        # 男性形は曜日と衝突しないため変換する (意図した非対称、docstring参照)。
        assert normalize_pt("quinto") == "5"
        assert normalize_pt("sexto") == "6"

    def test_ordinal_tens_plus_ambiguous_unit_untouched_atomically(self):
        # 序数10の位 + 曖昧クラス序数語は run 全体を不変換 (全か無か)。
        # 旧挙動の "10 quarto" 型混合出力 (部分変換) は禁止 (検収F8の修正)。
        assert normalize_pt("décimo quarto") == "décimo quarto"
        assert normalize_pt("décimo segundo") == "décimo segundo"
        assert normalize_pt("vigésima quinta") == "vigésima quinta"
        # 無曖昧な序数合成は引き続き変換される。
        assert normalize_pt("décimo quinto") == "15"
        assert normalize_pt("décimo primeiro") == "11"

    def test_conjunction_e_not_merged(self):
        # 1の位どうしの "e" は数詞列ではない ("dois e três" = 2 と 3)。
        assert normalize_pt("dois e três") == "2 e 3"


class TestCaseFoldingAndPunctuation:
    def test_case_folding(self):
        assert normalize_pt("Olá MUNDO") == normalize_pt("olá mundo")
        assert normalize_pt("OLÁ") == "olá"

    def test_diacritics_kept(self):
        # remove_diacritics=False (デフォルト): ã/ç 等は保持される
        # (avó と avo は別語)。
        assert normalize_pt("não") == "não"
        assert "ç" in normalize_pt("coração")

    def test_punctuation_removed(self):
        assert normalize_pt("Olá, mundo!") == "olá mundo"
        assert normalize_pt("O quê... o quê?") == "o quê o quê"

    def test_word_internal_apostrophe_kept(self):
        # §5 ステップ3の明示例外 (’→' 標準化を含む)。
        assert normalize_pt("d'água") == "d'água"
        assert normalize_pt("d’água") == normalize_pt("d'água")

    def test_nfkc(self):
        assert normalize_pt("２１") == "21"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "vinte e um",
        "trinta e três mil e quinhentos",
        "cento e vinte e três",
        "33.000",
        "3,14",
        "33.000,50",
        "um livro",
        "um segundo",
        "quinta",
        "décimo primeiro",
        "20º",
        "d'água",
        "não",
        "dois e três",
        "25-30",
        "1,000",  # 宣言済み衝突クラス: 1パス目で "1000" に確定し以後不動
        # 範囲超過の原子的ガード・余り位置の um・曖昧序数複合ガード:
        "cem mil",
        "duzentos mil e quinhentos",
        "cento e um",
        "mil e um",
        "décimo quarto",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_pt(sample)
            twice = normalize_pt(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizePt:
    def test_whitespace_split(self):
        assert tokenize_pt("Olá, mundo!") == ["olá", "mundo"]

    def test_empty_string(self):
        assert tokenize_pt("") == []
        assert tokenize_pt("   ") == []

    def test_matches_normalize_pt_split(self):
        text = "A loja tinha 25-30 artigos por 33.000 euros."
        assert tokenize_pt(text) == normalize_pt(text).split(" ")
