"""
normalizers/ru.py のテスト (PREREGISTRATION §5 準拠確認)。

ru.py のモジュールdocstringで宣言した各判断をピン留めする:
  - 基数の合成 (двадцать один=21、три тысячи триста=3300、
    тысяча девятьсот восемьдесят четыре=1984)
  - 特殊形 (сорок=40、девяносто=90、сто=100)
  - 格変化の線引き (頻出斜格セットは変換 / セット外の屈折形は不変換 /
    сорока はカササギと同形なので不変換)
  - ё/е 統一 (あいまい性 #1 で採用宣言)
  - 桁区切り (NBSP/narrow NBSP のみ除去、通常スペース・カンマは除去しない)
  - あいまいクラス不変換 (裸の тысячи/тысяч、序数、複合序数ガード、
    範囲超過 run)
  - 記号除去 / ケースフォールド / NFKC / アポストロフィ例外の不適用
  - 冪等性 (normalize(normalize(x)) == normalize(x))
  - tokenize_ru (空白分割 WER)
"""
from normalizers.ru import normalize_ru, tokenize_ru


class TestCardinalComposition:
    """§5.5: 基数の合成 (百→十→一の厳密降順 + тысяча スケール)。"""

    def test_simple_units(self):
        assert normalize_ru("пять") == "5"
        assert normalize_ru("девять") == "9"

    def test_compound_tens_units(self):
        assert normalize_ru("двадцать один") == "21"
        assert normalize_ru("тридцать семь") == "37"

    def test_teens_are_terminal(self):
        assert normalize_ru("пятнадцать") == "15"
        assert normalize_ru("сто двенадцать") == "112"

    def test_hundreds_composition(self):
        assert normalize_ru("сто двадцать пять") == "125"
        assert normalize_ru("девятьсот девяносто девять") == "999"

    def test_thousands_composition(self):
        assert normalize_ru("три тысячи триста") == "3300"
        assert normalize_ru("пять тысяч") == "5000"
        assert normalize_ru("две тысячи двадцать шесть") == "2026"

    def test_bare_thousand_nominative_singular(self):
        # 裸の тысяча (主格単数) は 1000。年号の読み下しに頻出する形も合成できる。
        assert normalize_ru("тысяча") == "1000"
        assert normalize_ru("тысяча девятьсот восемьдесят четыре") == "1984"

    def test_equivalence_with_digit_form(self):
        # 数値等価化の本来の目的: 綴りと数字が同一の正規化形へ落ちること。
        assert normalize_ru("двадцать один") == normalize_ru("21")
        assert normalize_ru("три тысячи триста") == normalize_ru("3300")

    def test_zero_is_standalone(self):
        assert normalize_ru("ноль") == "0"
        assert normalize_ru("нуль") == "0"
        # ноль は合成に参加しない (スコア読み等でトークンが消えないこと)。
        assert normalize_ru("двадцать ноль") == "20 0"
        assert normalize_ru("ноль ноль семь") == "0 0 7"

    def test_adjacent_numbers_stay_separate(self):
        # 降順が壊れる位置で数が区切られる (2つの独立した数)。
        assert normalize_ru("два три") == "2 3"
        assert normalize_ru("пять сто") == "5 100"

    def test_number_in_sentence_context(self):
        assert normalize_ru("ему двадцать один год") == "ему 21 год"


class TestSpecialForms:
    """§5.5: сорок / девяносто / сто の特殊形。"""

    def test_sorok(self):
        assert normalize_ru("сорок") == "40"
        assert normalize_ru("сорок два") == "42"

    def test_devyanosto(self):
        assert normalize_ru("девяносто") == "90"
        assert normalize_ru("девяносто один") == "91"

    def test_sto(self):
        assert normalize_ru("сто") == "100"
        assert normalize_ru("сто сорок") == "140"


class TestObliqueCaseBoundary:
    """あいまい性 #2: 格変化の線引き (頻出斜格セット内は変換、外は不変換)。"""

    def test_frequent_oblique_forms_converted(self):
        # 生格/与格/前置格 同形の頻出セット (ru.py docstring に全列挙)。
        assert normalize_ru("около пяти часов") == "около 5 часов"
        assert normalize_ru("более двадцати пяти лет") == "более 25 лет"
        assert normalize_ru("из ста") == "из 100"
        assert normalize_ru("двух") == "2"
        assert normalize_ru("девяноста") == "90"

    def test_oblique_with_yo_folded_first(self):
        # трёх/четырёх は ё→е 統一の後に照合される (語彙は е 形で登録)。
        assert normalize_ru("трёх") == "3"
        assert normalize_ru("четырёх") == "4"

    def test_out_of_set_inflections_untouched(self):
        # 頻出セット外の屈折形はあいまいクラス=不変換 (両側とも)。
        assert normalize_ru("одного") == "одного"
        assert normalize_ru("двумя") == "двумя"
        assert normalize_ru("пятью") == "пятью"
        assert normalize_ru("пятьюдесятью") == "пятьюдесятью"
        # 斜格の百位も頻出セット外。
        assert normalize_ru("двухсот") == "двухсот"

    def test_soroka_homograph_untouched(self):
        # сорока は 40 の生格でもあり普通名詞「カササギ」でもある同形異義語。
        # 決定論的に区別できないため不変換 (ru.py docstring で宣言)。
        assert normalize_ru("сорока") == "сорока"
        assert normalize_ru("около сорока лет") == "около сорока лет"

    def test_odin_nominative_is_converted(self):
        # один/одна/одно は「一人で」の語彙的用法があっても一律変換する
        # (採用理由は ru.py docstring あいまい性 #2、既知の許容ノイズ)。
        assert normalize_ru("один") == "1"
        assert normalize_ru("одна") == "1"
        assert normalize_ru("он остался один") == "он остался 1"


class TestAmbiguousClassesUntouched:
    """§5.5: あいまいクラスは両側とも不変換で残す。"""

    def test_bare_plural_thousand_untouched(self):
        # 裸の тысячи/тысяч は不定量表現 (несколько тысяч) と区別不能。
        assert normalize_ru("тысячи") == "тысячи"
        assert normalize_ru("несколько тысяч") == "несколько тысяч"
        assert normalize_ru("тысячи людей") == "тысячи людей"

    def test_ordinals_untouched(self):
        # あいまい性 #3: 序数は全部不変換 (性・格の屈折爆発のため)。
        assert normalize_ru("первый") == "первый"
        assert normalize_ru("второе") == "второе"
        assert normalize_ru("двадцатый век") == "двадцатый век"
        assert normalize_ru("в третьем классе") == "в третьем классе"

    def test_compound_ordinal_guard(self):
        # 基数 run の直後に序数形が続く場合は run 全体を不変換
        # (две тысячи двадцать шестой が「2020 шестой」に壊れないこと)。
        assert (
            normalize_ru("две тысячи двадцать шестой")
            == "две тысячи двадцать шестой"
        )
        assert normalize_ru("двадцать первого века") == "двадцать первого века"
        assert (
            normalize_ru("тысяча девятьсот восемьдесят четвертый год")
            == "тысяча девятьсот восемьдесят четвертый год"
        )

    def test_compound_ordinal_guard_does_not_overfire(self):
        # ガードは序数形トークンにのみ反応する: 基数+名詞は普通に変換される。
        assert normalize_ru("двадцать один год") == "21 год"
        assert normalize_ru("пять рублей") == "5 рублей"

    def test_compound_ordinal_guard_limited_to_compoundable_tails(self):
        # ガードの発火は run 末尾が十位/百位/千位語の場合に限る (検収で確定した
        # 過剰ブロックの修正)。一の位・11-19 で終わる run は複合序数の前半に
        # なり得ないため、直後の序数形があっても基数は変換される。
        assert normalize_ru("три первых места") == "3 первых места"
        assert normalize_ru("пять первых мест") == "5 первых мест"
        assert normalize_ru("двенадцать первых мест") == "12 первых мест"
        # 十位/百位/千位で終わる run は引き続きガードされる (複合序数)。
        assert normalize_ru("сто первый") == "сто первый"
        assert normalize_ru("сорок первый") == "сорок первый"
        assert (
            normalize_ru("две тысячи двадцать шестой")
            == "две тысячи двадцать шестой"
        )

    def test_out_of_range_run_untouched(self):
        # 合成結果が 99,999 を超える run は全体を不変換 (§5.5 の範囲は 0-99,999)。
        assert normalize_ru("сто тысяч") == "сто тысяч"
        assert normalize_ru("сто двадцать тысяч") == "сто двадцать тысяч"

    def test_out_of_scope_scale_word_stays(self):
        # миллион は範囲外スケール語なので語彙外 (係数のみ変換される。両側同一規則)。
        assert normalize_ru("два миллиона") == "2 миллиона"


class TestYoUnification:
    """あいまい性 #1: ё→е 統一 (採用宣言のピン留め)。"""

    def test_yo_folded_to_e(self):
        assert normalize_ru("ещё") == "еще"
        assert normalize_ru("зелёный") == "зеленый"

    def test_capital_yo_via_casefold(self):
        assert normalize_ru("Ёлка") == "елка"

    def test_engine_variants_equalized(self):
        # ё を打つエンジンと е で代用するエンジンが同一の正規化形になること。
        assert normalize_ru("зелёный") == normalize_ru("зеленый")
        assert normalize_ru("всё ещё") == normalize_ru("все еще")


class TestDigitGroupSeparator:
    """あいまい性 #4: 桁区切りは NBSP/narrow NBSP のみ除去 (保守的な線)。"""

    def test_nbsp_removed(self):
        assert normalize_ru("33\u00a0000") == "33000"
        assert normalize_ru("33\u00a0000") == normalize_ru("33000")

    def test_narrow_nbsp_removed(self):
        assert normalize_ru("33\u202f000") == "33000"

    def test_multiple_groups(self):
        assert normalize_ru("1\u00a0000\u00a0000") == "1000000"

    def test_regular_space_not_removed(self):
        # 通常スペースは千区切りとして扱わない (範囲・列挙との衝突回避)。
        assert normalize_ru("33 000") == "33 000"

    def test_range_output_not_collapsed(self):
        # §5.5 のレンジ規則: 25-30 → 25 30 のトークン境界化と衝突しないこと。
        assert normalize_ru("25-30") == "25 30"
        assert tokenize_ru("25-30") == ["25", "30"]

    def test_nbsp_not_matching_group_structure_untouched(self):
        # 直後が3桁ちょうどでない NBSP は千区切り条件を満たさず、NFKC で
        # 通常スペースに落ちてトークン境界として残る。
        assert normalize_ru("25\u00a030") == "25 30"

    def test_comma_is_decimal_not_group_separator(self):
        # ru のカンマは小数点。桁区切り除去の対象外で、一般句読点除去により
        # トークン境界になる (en の小数点ピリオドと同じ扱い)。
        assert normalize_ru("3,14") == "3 14"
        assert normalize_ru("33,000") == "33 000"


class TestCasePunctuationNFKC:
    """§5 手順1-4: NFKC / ケースフォールド / 記号除去 / 空白畳み込み。"""

    def test_case_folding_cyrillic(self):
        assert normalize_ru("Привет МИР") == "привет мир"
        assert normalize_ru("МОСКВА") == normalize_ru("москва")

    def test_punctuation_removed(self):
        assert normalize_ru("Привет, мир!") == "привет мир"
        assert normalize_ru("Что?.. Ничего — вообще.") == "что ничего вообще"

    def test_symbols_removed(self):
        assert normalize_ru("цена — 100 ₽") == "цена 100"

    def test_apostrophe_not_kept_in_ru(self):
        # ロシア語は Latin-script 言語ではないので §5 手順3のアポストロフィ
        # 例外は適用されない (ru.py docstring「アポストロフィの扱い」)。
        assert normalize_ru("д'Артаньян") == "д артаньян"
        assert normalize_ru("don't") == "don t"

    def test_nfkc_fullwidth_digits(self):
        assert normalize_ru("３３０００") == "33000"

    def test_whitespace_collapsed_not_stripped_out(self):
        # Amendment 1: ru は空白全除去の対象外。畳み込み+strip のみ。
        assert normalize_ru("привет   мир") == "привет мир"
        assert normalize_ru("  привет мир  ") == "привет мир"

    def test_latin_embedded_casefold(self):
        assert normalize_ru("Приложение Koedesk") == "приложение koedesk"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "двадцать один",
        "три тысячи триста",
        "тысяча девятьсот восемьдесят четыре",
        "две тысячи двадцать шестой",
        "три первых места",  # ガード限定の修正 (末尾一の位はガードしない)
        "сорок",
        "сорока",
        "около пяти часов",
        "несколько тысяч",
        "ещё зелёный",
        "33\u00a0000",
        "33 000",
        "25-30",
        "Привет, мир!",
        "д'Артаньян",
        "сто двадцать тысяч",
        "два миллиона",
        "ноль ноль семь",
        "он остался один",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_ru(sample)
            twice = normalize_ru(once)
            assert once == twice, (
                f"not idempotent for {sample!r}: {once!r} != {twice!r}"
            )


class TestTokenizeRu:
    """§5.6: ru は whitespace-delimited WER。"""

    def test_whitespace_split(self):
        assert tokenize_ru("Привет, мир!") == ["привет", "мир"]

    def test_numbers_tokenized_after_conversion(self):
        assert tokenize_ru("двадцать один год") == ["21", "год"]

    def test_empty_string(self):
        assert tokenize_ru("") == []
        assert tokenize_ru("   ") == []

    def test_matches_normalize_ru_split(self):
        text = "В магазине было двадцать пять товаров за 33\u00a0000 рублей."
        assert tokenize_ru(text) == normalize_ru(text).split(" ")
