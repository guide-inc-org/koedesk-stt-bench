"""
normalizers/en.py のテスト (PREREGISTRATION §5 準拠確認)。

§5.5 で明記された「パイロットで実際に監査した等価クラス」を最低限カバーする:
  - "seventy-eight" ≡ "78" (綴り基数→数字)
  - "twentieth century" ≡ "20th century" (綴り序数→数字、§5.5 最終形は裸の数字)
  - "33,000" ≡ "33000" (桁区切り除去)
  - ケースフォールディング
  - 句読点除去 + "don't" の語中アポストロフィ扱い
    (Whisper normalizer が縮約形を展開する実際の挙動をピン留めする)
  - 範囲 "25-30" → "25 30" (ハイフンがトークン境界化)
  - 冪等性 (normalize(normalize(x)) == normalize(x))
"""
from normalizers.en import normalize_en, tokenize_en


class TestNumberEquivalence:
    """§5.5: パイロット監査済みの数値等価クラス。"""

    def test_spelled_cardinal_equals_digit(self):
        assert normalize_en("seventy-eight") == normalize_en("78")
        assert normalize_en("seventy-eight") == "78"

    def test_spelled_ordinal_equals_digit_with_context(self):
        # §5.5: "twentieth"→"20th"→"20"。文脈込みで両者が完全一致すること。
        assert normalize_en("twentieth century") == normalize_en("20th century")
        assert normalize_en("twentieth century") == "20 century"

    def test_ordinal_ends_as_bare_digit(self):
        # Whisper normalizer 単体は "20th" のように接尾辞を残すが、
        # §5.5 は最終形を裸の数字と定めているので、接尾辞は必ず剥がれる。
        assert normalize_en("the 20th century") == "the 20 century"
        assert normalize_en("21st") == "21"
        assert normalize_en("32nd") == "32"
        assert normalize_en("103rd") == "103"

    def test_ordinal_suffix_stripped_but_plural_s_kept(self):
        # 複数形の "s" ("1960s") は序数接尾辞ではないので剥がさない。
        assert normalize_en("1960s") == "1960s"

    def test_digit_group_separator_removed(self):
        assert normalize_en("33,000") == normalize_en("33000")
        assert normalize_en("33,000") == "33000"

    def test_digit_group_separator_multiple_groups(self):
        assert normalize_en("1,000,000") == "1000000"

    def test_numeric_range_hyphen_becomes_token_boundary(self):
        # §5.5: レンジのハイフンは句読点除去でトークン境界になる。
        assert normalize_en("25-30") == "25 30"
        assert tokenize_en("25-30") == ["25", "30"]


class TestCaseFoldingAndPunctuation:
    def test_case_folding(self):
        assert normalize_en("Hello WORLD") == normalize_en("hello world")
        assert normalize_en("HELLO") == "hello"

    def test_punctuation_removed(self):
        assert normalize_en("Hello, World!") == "hello world"
        assert normalize_en("Wait... what?") == "wait what"

    def test_contraction_word_internal_apostrophe_and_whisper_expansion(self):
        # PREREGISTRATION §5 step3 は "don't" の語中アポストロフィを保持すると
        # 定めているが、§5.6 で適用される Whisper normalizer が縮約形を展開する
        # ため、最終的な正規化後テキストにアポストロフィは残らない。
        # この「展開される」という実際の挙動をここでピン留めする。
        assert normalize_en("don't") == "do not"
        assert normalize_en("I don't know") == "i do not know"
        assert normalize_en("can't") == "can not"
        assert normalize_en("won't") == "will not"

    def test_curly_apostrophe_standardized(self):
        # ’ (U+2019) を使った縮約形も同じ結果になること。
        assert normalize_en("don’t") == normalize_en("don't")

    def test_leading_trailing_quote_not_word_internal_removed(self):
        # 語頭・語末の引用符 (語中でない) は通常の句読点として除去される。
        assert normalize_en("'tis the season") == "tis the season"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "seventy-eight",
        "twentieth century",
        "20th century",
        "33,000",
        "don't",
        "25-30",
        "Hello, World!",
        "1960s",
        "the 274th regiment",
        "Twenty-One dollars and no cents",  # Whisper normalizerが$を合成するケース
        "colour vs color",
        "$5 million",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_en(sample)
            twice = normalize_en(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizeEn:
    def test_whitespace_split(self):
        assert tokenize_en("Hello, World!") == ["hello", "world"]

    def test_empty_string(self):
        assert tokenize_en("") == []
        assert tokenize_en("   ") == []

    def test_matches_normalize_en_split(self):
        text = "The store had 25-30 items for $33,000."
        assert tokenize_en(text) == normalize_en(text).split(" ")
