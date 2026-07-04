"""
normalizers/fr.py のテスト (PREREGISTRATION §5 準拠確認)。

§5.5 の数値等価クラス (基数・序数・桁区切り・小数)、曖昧クラスの不変換、
記号/ケース/NFKC/アポストロフィ、冪等性、tokenize を最低限カバーする
(test_en.py と同様式)。
"""
from normalizers.fr import normalize_fr, tokenize_fr


class TestNumberEquivalence:
    """§5.5: 数値等価クラス (フランス語)。"""

    def test_spelled_cardinal_equals_digit(self):
        assert normalize_fr("soixante-quinze") == normalize_fr("75")
        assert normalize_fr("soixante-quinze") == "75"
        assert normalize_fr("quatre-vingt-dix") == "90"
        assert normalize_fr("quatre-vingt-treize") == "93"
        assert normalize_fr("soixante-dix") == "70"
        assert normalize_fr("dix-sept") == "17"

    def test_et_un_composition(self):
        # "et" は <10の位> et un/une/onze の形でのみ数詞列として消費される。
        assert normalize_fr("vingt et un") == "21"
        assert normalize_fr("soixante et onze") == "71"

    def test_hundreds_and_thousands(self):
        assert normalize_fr("deux cent trois") == "203"
        assert normalize_fr("cent") == "100"
        assert normalize_fr("mille") == "1000"
        assert normalize_fr("trente-trois mille") == normalize_fr("33 000")
        assert normalize_fr("trente-trois mille") == "33000"
        assert normalize_fr("mille neuf cent quatre-vingt-quatre") == "1984"

    def test_un_participates_in_cent_mille_remainder(self):
        # cent/mille の余り位置は数詞列の内部 → un/une は数詞として参加する
        # (101/1001 の標準形。検収で確定したバグの修正)。
        assert normalize_fr("cent un") == "101"
        assert normalize_fr("cent une") == "101"
        assert normalize_fr("deux cent un") == "201"
        assert normalize_fr("mille un") == "1001"
        assert normalize_fr("mille et un") == "1001"
        assert normalize_fr("les mille et une nuits") == "les 1001 nuits"

    def test_out_of_range_run_left_untouched_atomically(self):
        # §5.5 範囲超過 (>99,999) は run 全体を不変換 — "100 1000" のような
        # 部分変換に割らない (検収で確定したバグの修正)。
        assert normalize_fr("cent mille") == "cent mille"
        assert normalize_fr("deux cent mille") == "deux cent mille"
        assert normalize_fr("deux cent mille cinq") == "deux cent mille cinq"

    def test_range_boundary_99999_still_converts(self):
        assert (
            normalize_fr(
                "quatre-vingt-dix-neuf mille neuf cent quatre-vingt-dix-neuf"
            )
            == "99999"
        )
        assert normalize_fr("quatre-vingt-dix-neuf mille") == "99000"

    def test_quatre_vingtieme_compound_ordinal(self):
        # quatre-vingtième=80番目。旧実装は "4 20" の壊れた部分変換だった
        # (検収の確認事項4の修正)。
        assert normalize_fr("quatre-vingtième") == "80"
        assert normalize_fr("le quatre-vingtième anniversaire") == "le 80 anniversaire"
        # 既存の複合序数終端は維持される。
        assert normalize_fr("quatre-vingt-dixième") == "90"
        assert normalize_fr("soixante-dixième") == "70"
        # cent の余り位置の unième 型序数終端 (deux-cent-unième=201番目)。
        assert normalize_fr("deux cent unième") == "201"

    def test_spelled_ordinal_ends_as_bare_digit(self):
        # §5.5: 序数の最終形は裸の数字 (en: twentieth→20th→20 と同じ扱い)。
        assert normalize_fr("le vingtième siècle") == normalize_fr("le 20ème siècle")
        assert normalize_fr("le vingtième siècle") == "le 20 siècle"
        assert normalize_fr("premier") == "1"
        assert normalize_fr("première") == "1"
        assert normalize_fr("deuxième") == "2"
        assert normalize_fr("vingt et unième") == "21"

    def test_digit_ordinal_suffix_stripped(self):
        assert normalize_fr("1er") == "1"
        assert normalize_fr("1re") == "1"
        assert normalize_fr("2e") == "2"
        assert normalize_fr("20ème") == "20"

    def test_digit_group_separator_removed(self):
        # フランス語の千区切りは空白 (NBSP/狭域NBSP を含む、§5.5 の言語別慣習行)。
        assert normalize_fr("33 000") == normalize_fr("33000")
        assert normalize_fr("33 000") == "33000"
        assert normalize_fr("33 000") == "33000"   # U+00A0 NBSP
        assert normalize_fr("33 000") == "33000"   # U+202F 狭域NBSP
        assert normalize_fr("1 000 000") == "1000000"

    def test_decimal_comma_normalized_to_dot_one_token(self):
        # フランス語の小数点は ","。"." に正規化して1トークンに保つ
        # (モジュールdocstringに明記した本実装の決定)。
        assert normalize_fr("3,14") == "3.14"
        assert tokenize_fr("3,14") == ["3.14"]
        assert normalize_fr("33 000,50") == "33000.50"

    def test_plain_number_pair_not_merged(self):
        # 「直後がちょうど3桁」でない数字の並びは融合しない。
        assert normalize_fr("25 30") == "25 30"
        assert normalize_fr("dix 3000") == "10 3000"  # 4桁は千区切りグループでない

    def test_thousands_fusion_reapplied_after_number_conversion(self):
        # 冪等性修正 (検収 high): 数詞変換が生成した数字の直後に3桁数字が
        # 続く形も1パス目で融合し尽くす ("10 300" で止まらない)。
        assert normalize_fr("dix 300") == "10300"
        assert normalize_fr("vingt 500 euros") == "20500 euros"
        assert normalize_fr("deux mille 300") == "2000300"

    def test_declared_fusion_noise_pinned(self):
        # 宣言済みノイズ (検収F9、モジュールdocstring): 「数字+ちょうど3桁」の
        # 並びは出所を問わず融合する。誤融合クラスの挙動をピン留めする。
        assert normalize_fr("en 2026 300 personnes") == "en 2026300 personnes"
        assert normalize_fr("en 2026 trois cents personnes") == "en 2026300 personnes"

    def test_numeric_range_hyphen_becomes_token_boundary(self):
        # §5.5: レンジのハイフンは句読点除去でトークン境界になる。
        assert normalize_fr("25-30") == "25 30"
        assert tokenize_fr("25-30") == ["25", "30"]


class TestAmbiguousClassesLeftUntouched:
    """§5.5: 曖昧クラスは変換しない (冠詞/数詞の文脈判定をしない)。"""

    def test_un_une_article_untouched(self):
        assert normalize_fr("un livre") == "un livre"
        assert normalize_fr("une pomme") == "une pomme"
        assert normalize_fr("un") == "un"
        assert normalize_fr("une") == "une"

    def test_un_converts_inside_number_sequence(self):
        # 数詞列の内部では un/une は数詞としてのみ現れるため変換に参加する
        # (cent/mille の余り位置も同じ「数詞列の内部」として一貫適用)。
        assert normalize_fr("vingt et un") == "21"
        assert normalize_fr("quatre-vingt-un") == "81"
        assert normalize_fr("trente et une") == "31"
        assert normalize_fr("cent un") == "101"
        assert normalize_fr("mille et un") == "1001"
        # 単独の un/une (冠詞) は引き続き不変換 (曖昧クラスの線引きは不変)。
        assert normalize_fr("un livre") == "un livre"
        assert normalize_fr("il lit un roman") == "il lit un roman"
        assert normalize_fr("une seule fois") == "une seule fois"

    def test_second_seconde_untouched(self):
        # second/seconde は序数2の異形と名詞「秒」の同形異義 → 変換しない
        # (deuxième は無曖昧なので変換する)。
        assert normalize_fr("second") == "second"
        assert normalize_fr("une seconde") == "une seconde"
        assert normalize_fr("deuxième") == "2"


class TestCaseFoldingAndPunctuationAndApostrophe:
    def test_case_folding(self):
        assert normalize_fr("Bonjour LE MONDE") == normalize_fr("bonjour le monde")
        assert normalize_fr("BONJOUR") == "bonjour"

    def test_diacritics_kept(self):
        # remove_diacritics=False (デフォルト): アクセントは保持される。
        assert normalize_fr("côté") == "côté"
        assert "é" in normalize_fr("répété")

    def test_punctuation_removed(self):
        assert normalize_fr("Bonjour, le monde !") == "bonjour le monde"
        assert normalize_fr("Quoi... quoi ?") == "quoi quoi"

    def test_word_internal_apostrophe_kept(self):
        # §5 ステップ3の明示例外。フランス語のエリジオンで特に重要。
        assert normalize_fr("l'homme") == "l'homme"
        assert normalize_fr("d'accord") == "d'accord"
        assert normalize_fr("aujourd'hui") == "aujourd'hui"

    def test_curly_apostrophe_standardized(self):
        assert normalize_fr("l’homme") == normalize_fr("l'homme")

    def test_nfkc(self):
        assert normalize_fr("２１") == "21"


class TestIdempotence:
    """normalize(normalize(x)) == normalize(x) を代表的なサンプルで確認する。"""

    SAMPLES = [
        "quatre-vingt-dix",
        "soixante-quinze",
        "vingt et un",
        "trente-trois mille",
        "33 000",
        "3,14",
        "33 000,50",
        "l'homme",
        "d'accord",
        "un livre",
        "une seconde",
        "le vingtième siècle",
        "1er",
        "25-30",
        "Bonjour, le monde !",
        # 冪等性修正の再現ケース (数詞変換が数字を生成 × 直後に3桁数字):
        "dix 300",
        "vingt 500 euros",
        "deux mille 300",
        "en 2026 trois cents personnes",
        "en 2026 300 personnes",
        "dix 3000",
        # 範囲超過の原子的ガード・cent/mille 余りの un・複合序数:
        "cent mille",
        "deux cent mille",
        "cent un",
        "mille et un",
        "quatre-vingtième",
        "",
        "   ",
    ]

    def test_idempotent(self):
        for sample in self.SAMPLES:
            once = normalize_fr(sample)
            twice = normalize_fr(once)
            assert once == twice, f"not idempotent for {sample!r}: {once!r} != {twice!r}"


class TestTokenizeFr:
    def test_whitespace_split(self):
        assert tokenize_fr("Bonjour, le monde !") == ["bonjour", "le", "monde"]

    def test_apostrophe_token_kept_whole(self):
        assert tokenize_fr("l'homme") == ["l'homme"]

    def test_empty_string(self):
        assert tokenize_fr("") == []
        assert tokenize_fr("   ") == []

    def test_matches_normalize_fr_split(self):
        text = "Le magasin avait 25-30 articles pour 33 000 euros."
        assert tokenize_fr(text) == normalize_fr(text).split(" ")
