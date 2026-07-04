"""normalizers/ko.py のテスト — PREREGISTRATION.md §5 (韓国語正規化) 準拠確認。

このテストファイルは §5.5 が要求する
「あいまいなクラスは normalizers/<lang>/numbers_test.py 相当のファイルで列挙する」
を満たす、韓国語の numbers_test.py 相当も兼ねる
(あいまいクラス列挙は TestAmbiguousClasses を参照)。

Amendment 1 スコープ注記 (ko keeps §5.4 as frozen) の確認:
分かち書きが保存されること自体を TestWhitespace でテストする。
"""

from normalizers.ko import normalize_ko, sino_korean_to_arabic, tokenize_ko


class TestNumberEquivalence:
    """§5.5: 漢数語→算用数字、桁区切り除去。"""

    def test_positional_mixed_33000_all_forms_equivalent(self):
        # 삼만삼천 / 3만3000 / 33,000 / 33000 は全て同一の正規化結果になる
        # (§5.5 が ja について明記する positional mixed forms の ko 対応)。
        assert sino_korean_to_arabic("삼만삼천") == "33000"
        assert sino_korean_to_arabic("3만3000") == "33000"
        assert (
            normalize_ko("삼만삼천")
            == normalize_ko("3만3000")
            == normalize_ko("33,000")
            == normalize_ko("33000")
            == "33000"
        )

    def test_positional_building_blocks(self):
        # 位取り合成の基本ブロック (すべて位文字を含む長さ2以上の run)。
        assert sino_korean_to_arabic("이십") == "20"
        assert sino_korean_to_arabic("이십오") == "25"
        assert sino_korean_to_arabic("십오") == "15"
        assert sino_korean_to_arabic("구십구") == "99"
        assert sino_korean_to_arabic("오백") == "500"
        assert sino_korean_to_arabic("삼천오백") == "3500"
        assert sino_korean_to_arabic("만삼천") == "13000"  # 만 の暗黙係数1

    def test_mixed_ascii_hangul_forms(self):
        assert sino_korean_to_arabic("3천500") == "3500"
        assert sino_korean_to_arabic("3만5천") == "35000"

    def test_number_with_following_counter_still_converts(self):
        # 数字 + 助数詞は変換される (run は数詞文字で途切れるため助数詞は残る)。
        assert normalize_ko("삼만삼천 원") == "33000 원"
        assert normalize_ko("이십오 명") == "25 명"

    def test_digit_group_separator_removed(self):
        assert normalize_ko("33,000") == "33000"
        # 桁区切り除去は変換 (0-99,999) とは独立の規則なので範囲上限を持たない。
        assert normalize_ko("1,000,000") == "1000000"
        # 全角カンマ・全角数字は NFKC が先に統一する。
        assert normalize_ko("１，２３４，５６７") == "1234567"

    def test_out_of_range_not_converted(self):
        # 0〜99,999 の範囲外は不変換 (십만=100000、천만=10^7)。
        assert sino_korean_to_arabic("십만") == "십만"
        assert sino_korean_to_arabic("천만") == "천만"
        # 「천만에요 (どういたしまして)」が数値化されない (範囲チェックの実効果)。
        assert normalize_ko("천만에요") == "천만에요"

    def test_ordinal_je_prefix(self):
        # 漢数語序数 제N: ja の 第二十→第20 と同型 (제 は残し数部分のみ変換)。
        assert sino_korean_to_arabic("제이십") == "제20"
        assert normalize_ko("제이십") == normalize_ko("제20") == "제20"
        assert sino_korean_to_arabic("제삼십오") == "제35"


class TestAmbiguousClasses:
    """§5.5: あいまいクラスの列挙 — 意図的に変換しない (untouched) ことを保証する。"""

    # 固有語数詞: 系統ごと丸ごと曖昧クラス (変換対象文字を含まないため構造的に不変換)。
    NATIVE_NUMERALS = [
        "하나", "둘", "셋", "넷", "다섯", "여섯", "일곱", "여덟", "아홉",
        "열", "스물", "서른",
        "한", "두", "세",  # 連体形 (한=1/おおよそ/「した」等の多義)
    ]

    # 単音節 sino run: 同綴り異義が支配的 (일=仕事/日、이=この/歯/助詞、
    # 만=〜だけ/万 …)。長さ2以上 + 位文字必須の構造規則で除外される。
    SINGLE_SYLLABLES = ["일", "이", "삼", "사", "오", "십", "백", "천", "만"]

    # 桁読み表記 / 数詞音節のみで構成される一般語: 位文字なし run は不変換。
    DIGIT_READING_AND_HOMOGRAPHS = [
        "이공이육",  # 2026 の桁読み — 変換しない (下記の一般語を守るため)
        "사이",      # 間
        "오이",      # きゅうり
        "이사",      # 引っ越し
        "구이",      # 焼き物
    ]

    # 概数複合: 位文字直前の係数が漢数語2音節以上 → パース失敗で不変換。
    APPROXIMATE_COMPOUNDS = ["이삼십", "삼사십", "십이삼"]

    # 語彙化ブロックリスト (run 完全一致)。오만 は FLEURS ko 実測破損 [31] に
    # より 2026-07-05 追加 (ko.py docstring 変換条件3)。
    LEXICALIZED_BLOCKLIST = ["만일", "만이", "천사", "만사", "오만"]

    # 固有語序数・語彙化した漢数語序数。
    ORDINAL_AMBIGUOUS = ["첫째", "둘째", "셋째", "제일", "제이"]

    def test_native_numerals_left_untouched(self):
        for word in self.NATIVE_NUMERALS:
            assert normalize_ko(word) == word, f"{word!r} は変換されずに残るべき"

    def test_single_syllable_sino_left_untouched(self):
        for word in self.SINGLE_SYLLABLES:
            assert sino_korean_to_arabic(word) == word, f"{word!r} は変換されずに残るべき"

    def test_digit_reading_and_homographs_left_untouched(self):
        for word in self.DIGIT_READING_AND_HOMOGRAPHS:
            assert sino_korean_to_arabic(word) == word, f"{word!r} は変換されずに残るべき"

    def test_approximate_compounds_left_untouched(self):
        for word in self.APPROXIMATE_COMPOUNDS:
            assert sino_korean_to_arabic(word) == word, f"{word!r} は変換されずに残るべき"

    def test_lexicalized_blocklist_left_untouched(self):
        for word in self.LEXICALIZED_BLOCKLIST:
            assert sino_korean_to_arabic(word) == word, f"{word!r} は変換されずに残るべき"

    def test_ordinals_ambiguous_left_untouched(self):
        # 제일 (「最も」=第一)・제이 (第二) は単音節規則で自然に不変換。
        # 첫째/둘째 は固有語系統で構造的に不変換。
        for word in self.ORDINAL_AMBIGUOUS:
            assert normalize_ko(word) == word, f"{word!r} は変換されずに残るべき"

    def test_ambiguous_classes_left_untouched_in_context(self):
        # 文中でも同様にあいまいクラスは変換されないことを確認する。
        assert normalize_ko("만일에 대비한다") == "만일에 대비한다"
        assert normalize_ko("너만이 할 수 있다") == "너만이 할 수 있다"
        assert normalize_ko("천사 같은 사람") == "천사 같은 사람"
        assert normalize_ko("만사가 귀찮다") == "만사가 귀찮다"
        assert normalize_ko("일이 많다") == "일이 많다"      # 일(仕事)+이(助詞)
        assert normalize_ko("사이가 좋다") == "사이가 좋다"
        assert normalize_ko("사과를 하나 먹었다") == "사과를 하나 먹었다"

    def test_unparseable_myriad_duplication_left_untouched(self):
        # 만 の重複 (만만하다 の「만만」等、ja パイロットの「1万万」対応と同型)
        # はクラッシュせず不変換。
        assert sino_korean_to_arabic("만만") == "만만"
        assert normalize_ko("그는 만만하지 않다") == "그는 만만하지 않다"


class TestFleursHeadlineBreakages:
    """FLEURS ko 見出しセット 200発話の検収で実際に発火した破損 2件の再現と、
    その修正 (run 開始境界ガード=変換条件4・오만 ブロックリスト=変換条件3) が
    検収確認済みの正常挙動を壊さないことの保証 (2026-07-05)。"""

    def test_lexicalized_oman_left_untouched(self):
        # 再現ケース (修正前 fail): [31]「오만하다」(傲慢だ) → 50000하다。
        # run は「오만」ちょうど (하다 は数詞文字集合外) — 完全一致ブロック。
        assert sino_korean_to_arabic("오만하다") == "오만하다"
        assert normalize_ko("그는 오만하다") == "그는 오만하다"
        # 国名オマーン (同綴り) も同様に保護される。
        assert normalize_ko("오만의 수도") == "오만의 수도"

    def test_oman_blocklist_tradeoff_declared(self):
        # トレードオフの宣言 (ko.py docstring 変換条件3): 数値読みの 오만
        # (오만 원=5万ウォン) も run 完全一致で不変換になる。ref/hyp 双方
        # 同一規則の宣言済みノイズ。
        assert normalize_ko("오만 원") == "오만 원"
        # 長い run の部分文字列としての 오만 は完全一致でないため変換される。
        assert sino_korean_to_arabic("오만삼천") == "53000"

    def test_word_internal_run_left_untouched(self):
        # 再現ケース (修正前 fail): [27]「돌연변이만이」→ 돌연변20002
        # (어절内の途中から run「이만이」を拾っていた)。変換条件4の
        # run 開始境界ガードで構造的に排除する。
        assert sino_korean_to_arabic("돌연변이만이") == "돌연변이만이"
        assert normalize_ko("돌연변이만이 남는다") == "돌연변이만이 남는다"

    def test_verified_normal_behaviors_maintained(self):
        # 検収で確認済みの正常挙動の維持 (タスク指定の5点 + 数字先頭 run)。
        assert normalize_ko("삼만 삼천") == "30000 3000"
        assert sino_korean_to_arabic("제이십일") == "제21"
        assert normalize_ko("천만에요") == "천만에요"
        assert sino_korean_to_arabic("수백만") == "수백만"
        assert sino_korean_to_arabic("이천사년") == "2004년"
        # 数字+位文字の混在 run はハングル直後・어절途中でも正当 (変換条件4(iii))。
        assert normalize_ko("1만 2천") == "10000 2000"
        assert normalize_ko("제21과") == "제21과"
        assert sino_korean_to_arabic("약3만") == "약30000"


class TestPunctuationCaseNFKC:
    """§5 手順1-3: NFKC、ケースフォールド、記号除去 (アポストロフィ例外なし)。"""

    def test_punctuation_removed(self):
        assert normalize_ko("안녕하세요, 세계!") == "안녕하세요 세계"
        assert normalize_ko("정말...그래요?") == "정말 그래요"
        assert normalize_ko("“인용”과 『책』") == "인용 과 책"

    def test_case_folding_on_embedded_latin(self):
        assert normalize_ko("KOREA 좋아") == "korea 좋아"
        assert normalize_ko("AI 시대") == normalize_ko("ai 시대")

    def test_nfkc_fullwidth_latin_and_digits(self):
        assert normalize_ko("ＡＢＣ１２３") == "abc123"

    def test_apostrophe_removed_no_latin_exception(self):
        # ko は「Latin-script languages」に該当しないため、§5 手順3の語中
        # アポストロフィ例外は適用されない (読みA、モジュールdocstring参照)。
        # 挙動をここでピン留めする。
        assert normalize_ko("let's go 시작") == "let s go 시작"


class TestWhitespace:
    """§5.4 凍結 + Amendment 1 スコープ注記: ko は空白全除去の対象外。"""

    def test_word_spacing_is_preserved(self):
        # 分かち書き (単語間の単一スペース) はそのまま保存される。
        assert normalize_ko("아버지가 방에 들어가신다") == "아버지가 방에 들어가신다"

    def test_spacing_difference_remains_a_real_difference(self):
        # 分かち書きの有無は正書法上の実差として正規化後も区別される
        # (ja/zh/th のような空白全除去は行わない)。
        assert normalize_ko("아버지가 방에") != normalize_ko("아버지가방에")

    def test_whitespace_runs_collapsed_and_stripped(self):
        assert normalize_ko("안녕   하세요") == "안녕 하세요"
        assert normalize_ko("  안녕하세요  ") == "안녕하세요"
        assert normalize_ko("안녕\t하세요\n반가워요") == "안녕 하세요 반가워요"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "삼만삼천 원을 냈다",
        "3만3000",
        "33,000",
        "제이십 회 대회",
        "만일에 대비해 이십오 명이 왔다",
        "천만에요, 사이가 좋아요!",
        "ＡＢＣ１２３ let's go",
        "아버지가   방에 들어가신다",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_ko(sample)
            twice = normalize_ko(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizeKo:
    """§5.6 (ko): 空白分割 WER トークナイザ。"""

    def test_whitespace_split(self):
        assert tokenize_ko("안녕하세요, 세계!") == ["안녕하세요", "세계"]

    def test_number_converted_before_split(self):
        assert tokenize_ko("삼만삼천 원을 냈다") == ["33000", "원을", "냈다"]

    def test_empty_string(self):
        assert tokenize_ko("") == []
        assert tokenize_ko("   ") == []

    def test_matches_normalize_ko_split(self):
        text = "제이십 회 대회에 이십오 명이 왔다."
        assert tokenize_ko(text) == normalize_ko(text).split(" ")
