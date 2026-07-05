"""normalizers/th.py のテスト — PREREGISTRATION.md §5 (タイ語正規化) 準拠確認。

このテストファイルは §5.5 が要求する
「あいまいなクラスは normalizers/<lang>/numbers_test.py 相当のファイルで列挙する」
を満たす、タイ語の numbers_test.py 相当も兼ねる (数詞変換のあいまいクラス
列挙は TestAmbiguousClasses を参照)。

§5.6: th は「no word segmentation; CER only」— tokenize_th は存在しないこと
自体もここでアサートする。Amendment 1 (§5.4 改訂: th は CER 前に全空白除去、
凍結版と併記) の二値フラグ両側の挙動も検証する。
"""

from normalizers.th import (
    cer_chars_th,
    normalize_th,
    thai_digits_to_arabic,
    thai_numerals_to_arabic,
)


# --------------------------------------------------------------------------
# §5.5 タイ数字 ๐-๙ → アラビア数字 (NFKCでは変換されないため明示変換)
# --------------------------------------------------------------------------


class TestThaiDigits:
    def test_thai_digits_converted(self):
        assert thai_digits_to_arabic("๐๑๒๓๔๕๖๗๘๙") == "0123456789"
        assert normalize_th("๒๕๖๙") == "2569"

    def test_nfkc_alone_does_not_convert_thai_digits(self):
        # 実装前提の確認: NFKC はタイ数字を変換しない (だから明示変換が必要)。
        import unicodedata

        assert unicodedata.normalize("NFKC", "๑๒๓") == "๑๒๓"

    def test_thai_digits_with_group_separator(self):
        # タイ数字→ASCII化の後に桁区切り除去が効く (๓๓,๐๐๐ → 33000)。
        assert normalize_th("๓๓,๐๐๐") == "33000"
        assert normalize_th("33,000") == "33000"


# --------------------------------------------------------------------------
# §5.5 綴りタイ語数詞→算用数字
# --------------------------------------------------------------------------


class TestSpelledNumerals:
    def test_single_digits(self):
        assert thai_numerals_to_arabic("หนึ่ง") == "1"
        assert thai_numerals_to_arabic("สอง") == "2"
        assert thai_numerals_to_arabic("เก้า") == "9"

    def test_positional_building_blocks(self):
        assert thai_numerals_to_arabic("สิบ") == "10"
        assert thai_numerals_to_arabic("สิบห้า") == "15"
        assert thai_numerals_to_arabic("สามสิบ") == "30"
        assert thai_numerals_to_arabic("ร้อย") == "100"
        assert thai_numerals_to_arabic("ห้าร้อย") == "500"
        assert thai_numerals_to_arabic("พัน") == "1000"
        assert thai_numerals_to_arabic("สามพันห้าร้อย") == "3500"
        assert thai_numerals_to_arabic("หมื่น") == "10000"
        assert thai_numerals_to_arabic("ห้าหมื่น") == "50000"

    def test_yi_special_form_for_twenty(self):
        # ยี่ は สิบ の直前でのみ 2 (ยี่สิบ=20。สองสิบ とは書かない)。
        assert thai_numerals_to_arabic("ยี่สิบ") == "20"
        assert thai_numerals_to_arabic("ยี่สิบสาม") == "23"

    def test_et_special_form_for_final_one(self):
        # เอ็ด は位取り語の後の末尾1の位でのみ 1。
        assert thai_numerals_to_arabic("สิบเอ็ด") == "11"
        assert thai_numerals_to_arabic("ยี่สิบเอ็ด") == "21"
        assert thai_numerals_to_arabic("ร้อยเอ็ด") == "101"

    def test_full_composition(self):
        # สองพันสามร้อยสี่สิบห้า = 2345
        assert thai_numerals_to_arabic("สองพันสามร้อยสี่สิบห้า") == "2345"
        # หนึ่งหมื่นสองพันสามร้อยสี่สิบห้า = 12345
        assert thai_numerals_to_arabic("หนึ่งหมื่นสองพันสามร้อยสี่สิบห้า") == "12345"

    def test_number_followed_by_ordinary_word_still_converts(self):
        # タイ語は数詞と後続語の間にスペースを置かないことがあるが、
        # 非あいまいな後続語なら変換される (ห้าปี=5年、สองคน=2人)。
        assert thai_numerals_to_arabic("ห้าปี") == "5ปี"
        assert thai_numerals_to_arabic("สองคน") == "2คน"

    def test_invalid_special_forms_left_untouched(self):
        # 特殊形の誤用は解析不能として不変換で残す (§5.5「解析不能は触らない」)。
        assert thai_numerals_to_arabic("เอ็ด") == "เอ็ด"        # 単独のเอ็ด
        assert thai_numerals_to_arabic("ยี่ห้อ") == "ยี่ห้อ"      # ยี่ の後にสิบが無い (「ブランド」)
        assert thai_numerals_to_arabic("เอ็ดสิบ") == "เอ็ดสิบ"   # เอ็ดが先頭

    def test_consecutive_digit_words_left_untouched(self):
        # 数字語の連続 (電話番号の読み上げ/列挙と区別不能) は変換しない —
        # th は桁読みモードを持たない (th.py docstring 参照)。
        assert thai_numerals_to_arabic("หนึ่งสองสาม") == "หนึ่งสองสาม"

    def test_non_descending_units_left_untouched(self):
        # สิบพัน のような位取りの非文は解析不能として不変換。
        assert thai_numerals_to_arabic("สิบพัน") == "สิบพัน"


# --------------------------------------------------------------------------
# §5.5 あいまいクラスの列挙 — 意図的に変換しない (untouched) ことを保証する
# --------------------------------------------------------------------------


AMBIGUOUS_CLASSES = [
    "ห้าม",      # 「禁じる」(ห้า=5 + ม) — ブロックリスト
    "สามารถ",    # 「できる」(สาม=3 + ารถ) — ブロックリスト
    "เก้าอี้",    # 「椅子」(เก้า=9 + อี้) — ブロックリスト
    "หกล้ม",     # 「転ぶ」(หก=6 + ล้ม) — ブロックリスト
    "พันเอก",    # 「大佐」(พัน=1000 + เอก) — ブロックリスト
    "ร้อยเอก",   # 「大尉」(ร้อย=100 + เอก) — ブロックリスト
    "ศูนย์",     # 数詞0だが「中心・センター」と同綴りの多義語 — 語彙全体を対象外
    "เอ็ด",      # 単独のเอ็ด (数値でない) — 構造規則で解析不能
    "ยี่ห้อ",     # 「ブランド」(ยี่ の後に สิบ が無い) — 構造規則で解析不能
    # -- FLEURS th 実測破損 (見出し200発話中21発話) に基づく拡充 --
    "สายพันธุ์",  # 「品種・種」(สาย+พัน+ธุ์) — ブロックリスト พันธ で包含
    "พันธุ์",     # 「種」(พัน+ธุ์) — 同上
    "ความสัมพันธ์",  # 「関係」(สัม+พัน+ธ์) — ブロックリスト สัมพันธ/พันธ で包含
    "กองพัน",    # 「大隊」(กอง+พัน) — 語末数詞綴り。前方文脈を見る包含判定で除外
    "สามี",      # 「夫」(สาม+ี) — 構造ガード (直後の従属母音記号) + ブロックリスト
    "ห้าง",      # 「店・デパート」(ห้า+ง) — ブロックリスト
    "สิบเอก",    # 「軍曹」(สิบ+เอก) — ブロックリスト
    "สามัคคี",   # 「団結」(สาม+ัคคี) — 構造ガード + ブロックリスト
    "สามัญ",     # 「普通の」(สาม+ัญ) — 構造ガード + ブロックリスト
    "เรียบร้อย",  # 「きちんと・完了」(เรียบ+ร้อย) — 語末数詞綴り。包含判定で除外
    "โกหก",      # 「嘘をつく」(โก+หก) — 語末数詞綴り。Track A参照文監査 2026-07-05 検出
]


class TestAmbiguousClasses:
    def test_ambiguous_classes_left_untouched(self):
        for word in AMBIGUOUS_CLASSES:
            assert thai_numerals_to_arabic(word) == word, f"{word!r} は変換されずに残るべき"

    def test_ambiguous_classes_left_untouched_in_context(self):
        assert normalize_th("ห้ามเข้า") == "ห้ามเข้า"                # 立入禁止
        assert normalize_th("เขาสามารถไปได้") == "เขาสามารถไปได้"    # 彼は行ける
        assert normalize_th("นั่งบนเก้าอี้") == "นั่งบนเก้าอี้"        # 椅子に座る
        assert normalize_th("ระวังหกล้ม") == "ระวังหกล้ม"            # 転倒注意
        assert normalize_th("ศูนย์การค้า") == "ศูนย์การค้า"          # ショッピングセンター
        assert normalize_th("ศูนย์กลางเมือง") == "ศูนย์กลางเมือง"    # 街の中心

    def test_zero_word_never_converts_even_alone(self):
        # ศูนย์ は単独でも変換しない (多義語のため語彙全体を対象外にした設計判断)。
        # 数値0はタイ数字 ๐ / ASCII 0 で正規化される。
        assert normalize_th("ศูนย์") == "ศูนย์"
        assert normalize_th("๐") == "0"


# --------------------------------------------------------------------------
# 構造ガード (run 直後の従属母音記号・声調記号) + ブロックリスト拡充
# — FLEURS th 参照文の実測破損 (200発話中21発話) の再現テスト
# --------------------------------------------------------------------------


class TestWordInternalSyllableGuard:
    def test_structural_guard_following_dependent_sign(self):
        # run 直後が従属母音記号等 = run が語の途中で切れている確定的証拠
        # → 不変換 (th.py docstring【構造ガード】案B)。
        assert thai_numerals_to_arabic("สามี") == "สามี"        # 夫 (旧実装: 3ี)
        assert thai_numerals_to_arabic("สามัคคี") == "สามัคคี"   # 団結 (旧: 3ัคคี)
        assert thai_numerals_to_arabic("สามัญ") == "สามัญ"      # 普通の (旧: 3ัญ)

    def test_lexicalized_blocklist_fleurs_patterns(self):
        # FLEURS th 参照文で実際に破損した一般語 (検収レポート記載の再現)。
        assert normalize_th("สายพันธุ์ใหม่") == "สายพันธุ์ใหม่"    # 新種 (旧: สาย1000ธุ์ใหม่)
        assert normalize_th("ความสัมพันธ์") == "ความสัมพันธ์"     # 関係 (旧: ความสัม1000ธ์)
        assert normalize_th("กองพันทหาร") == "กองพันทหาร"       # 大隊 (旧: กอง1000ทหาร)
        assert normalize_th("ห้างสรรพสินค้า") == "ห้างสรรพสินค้า"  # デパート (旧: 5งสรรพสินค้า)
        assert normalize_th("สิบเอก") == "สิบเอก"                # 軍曹 (旧: 10เอก)
        assert normalize_th("เรียบร้อยแล้ว") == "เรียบร้อยแล้ว"    # 完了 (旧: เรียบ100แล้ว)
        # Track A 参照文監査 (2026-07-05・FLEURS th_0018/th_0128) で実測破損した一般語。
        assert normalize_th("เขาโกหกเรา") == "เขาโกหกเรา"        # 彼は我々に嘘をついた (旧: เขาโก6เรา)

    def test_roi_la_percentage_still_converts(self):
        # ร้อยละ (百分率) は真正の数値表現なので変換のまま
        # (th.py docstring【あいまいクラス】の「ブロックしない判断」を参照)。
        assert thai_numerals_to_arabic("ร้อยละ") == "100ละ"
        assert thai_numerals_to_arabic("ร้อยละห้า") == "100ละ5"

    def test_legit_conversions_not_over_blocked(self):
        # 構造ガード/ブロックリスト拡充後も正当な変換は維持される
        # (「直後がタイ文字なら常に不変換」案Aを退けた理由の実証)。
        assert thai_numerals_to_arabic("ยี่สิบเอ็ด") == "21"
        assert thai_numerals_to_arabic("สามสิบบาท") == "30บาท"
        assert thai_numerals_to_arabic("ห้าปี") == "5ปี"
        assert thai_numerals_to_arabic("ห้าร้อยห้าสิบห้า") == "555"


# --------------------------------------------------------------------------
# 貪欲 run のバックオフ (最長成功プレフィックス) — th.py docstring 参照
# --------------------------------------------------------------------------


class TestGreedyRunBackoff:
    def test_yisip_yiho_backoff(self):
        # 貪欲 run「ยี่สิบยี่」(パース不能) → 最長成功プレフィックス ยี่สิบ=20 に
        # バックオフし、残り (ยี่ห้อ=ブランド) は不変換で残す (検収レポート再現:
        # 旧実装は run 全体不変換で 20 が数値化されなかった)。
        assert thai_numerals_to_arabic("ยี่สิบยี่ห้อ") == "20ยี่ห้อ"
        assert normalize_th("มียี่สิบยี่ห้อ") == "มี20ยี่ห้อ"

    def test_backoff_does_not_break_enumeration(self):
        # 数字語の列挙は従来どおり不変換 (バックオフ条件(i): プレフィックスに
        # 位取り語が無いため対象外)。
        assert thai_numerals_to_arabic("หนึ่งสองสาม") == "หนึ่งสองสาม"
        assert thai_numerals_to_arabic("หนึ่งสองสามสี่ห้า") == "หนึ่งสองสามสี่ห้า"

    def test_backoff_rejected_when_remainder_parses_as_number(self):
        # 残りも数としてパース可能なら連続数/読み上げの可能性 → run 全体を
        # 不変換 (バックオフ条件(ii)。สิบพัน 等の位取り非文も従来どおり不変換)。
        assert thai_numerals_to_arabic("สิบพัน") == "สิบพัน"
        assert thai_numerals_to_arabic("ยี่สิบยี่สิบ") == "ยี่สิบยี่สิบ"

    def test_backoff_is_idempotent(self):
        # バックオフ出力を再正規化しても変化しない。
        once = normalize_th("ยี่สิบยี่ห้อ")
        assert normalize_th(once) == once == "20ยี่ห้อ"


# --------------------------------------------------------------------------
# §5 手順3: 記号・句読点の除去 (Unicode category P*/S*)、タイ文字の結合記号は保持
# --------------------------------------------------------------------------


class TestPunctuationRemoval:
    def test_punctuation_removed(self):
        assert normalize_th('เขาพูดว่า "สวัสดี" ครับ') == "เขาพูดว่า สวัสดี ครับ"

    def test_thai_combining_marks_preserved(self):
        # 声調記号・母音記号 (Mn) は P*/S* ではないため失われない。
        text = "เสียงชัดเจนมาก"  # ั (MAI HAN-AKAT, Mn) と ้ (声調記号, Mn) を含む
        assert normalize_th(text) == text

    def test_sara_am_decomposed_by_nfkc(self):
        # ำ (U+0E33 SARA AM) は NFKC で ํ (U+0E4D) + า (U+0E32) に分解される
        # (§5 手順1 の宣言済み効果。ref/hyp 双方同一適用。th.py docstring参照)。
        import unicodedata

        assert normalize_th("น้ำ") == unicodedata.normalize("NFKC", "น้ำ")
        assert "ํา" in normalize_th("น้ำ")

    def test_thai_letter_like_marks_preserved(self):
        # ๆ (U+0E46 MAIYAMOK) は Lm、ฯ (U+0E2F PAIYANNOI) は Lo であり、
        # いずれも P*/S* に属さないため除去されない (実測カテゴリ確認済み)。
        assert normalize_th("เร็วๆ") == "เร็วๆ"
        assert normalize_th("ฯลฯ") == "ฯลฯ"

    def test_nfkc_fullwidth_latin_and_digits(self):
        assert normalize_th("ＡＢＣ") == "abc"
        assert normalize_th("１２３") == "123"


# --------------------------------------------------------------------------
# §5 手順4: 空白 — 凍結版 (畳み込みのみ) vs Amendment 1 (全除去) の二値フラグ
# タイ語の正書法は単語間スペースを使わないが、文区切り等にスペースが現れる。
# --------------------------------------------------------------------------


class TestWhitespaceFlag:
    def test_default_keeps_single_spaces(self):
        assert normalize_th("สวัสดีครับ วันนี้อากาศดี") == "สวัสดีครับ วันนี้อากาศดี"
        assert normalize_th("สวัสดีครับ   วันนี้อากาศดี") == "สวัสดีครับ วันนี้อากาศดี"
        assert normalize_th("  สวัสดีครับ  ") == "สวัสดีครับ"

    def test_strip_all_flag_removes_internal_spaces_too(self):
        assert (
            normalize_th("สวัสดีครับ วันนี้อากาศดี", strip_all_whitespace_for_cer=True)
            == "สวัสดีครับวันนี้อากาศดี"
        )
        assert (
            normalize_th("สวัสดีครับวันนี้อากาศดี", strip_all_whitespace_for_cer=True)
            == "สวัสดีครับวันนี้อากาศดี"
        )

    def test_both_modes_agree_when_no_internal_spaces(self):
        ref = "วันนี้อากาศดี"
        assert normalize_th(ref) == normalize_th(ref, strip_all_whitespace_for_cer=True)


# --------------------------------------------------------------------------
# Amendment 3: True側の全空白除去は数値変換の**前** (th.py docstring
# 【処理順 — Amendment 3】参照)
# --------------------------------------------------------------------------


class TestAmendment3WhitespaceBeforeNumbers:
    def test_segmented_numeral_reassembled(self):
        # 再現ケース (修正前 fail): 分かち書きエンジンの数詞断片化。旧実装は
        # สามหมื่น/สามพัน を独立変換してから空白除去し '300003000' を合成した。
        assert (
            normalize_th("สามหมื่น สามพัน", strip_all_whitespace_for_cer=True)
            == "33000"
        )

    def test_blocklist_protection_survives_space_removal(self):
        # 数詞綴りを語末に含む一般語が分かち書きされても、空白除去後の包含判定
        # が効く (旧実装は ร้อย→100 と変換して 'เรียบ100' に破損した)。
        assert (
            normalize_th("เรียบ ร้อย", strip_all_whitespace_for_cer=True)
            == "เรียบร้อย"
        )

    def test_unparseable_merged_run_left_untouched(self):
        # 結合の結果パース不能になる run (位取り非文 สิบพัน) は従来どおり
        # 全体不変換 (バックオフ条件(ii) が連続数の誤結合も防ぐ)。
        assert (
            normalize_th("สิบ พัน", strip_all_whitespace_for_cer=True)
            == "สิบพัน"
        )

    def test_false_side_order_unchanged(self):
        # False側 (凍結字義モード) は処理順不変 — 従来どおり独立変換のまま。
        assert normalize_th("สามหมื่น สามพัน") == "30000 3000"


# --------------------------------------------------------------------------
# §5.6: th は CER only — tokenize_th は存在しない / CER文字列
# --------------------------------------------------------------------------


class TestCerOnly:
    def test_tokenize_th_does_not_exist(self):
        # §5.6「no word segmentation; CER only (WER column shows "—")」の凍結どおり、
        # WERトークナイザを提供しないこと自体を仕様としてアサートする。
        import normalizers.th as th_module

        assert not hasattr(th_module, "tokenize_th")

    def test_cer_chars_th_is_character_sequence(self):
        normalized = normalize_th("วันนี้อากาศดี", strip_all_whitespace_for_cer=True)
        assert cer_chars_th(normalized) == list(normalized)
        assert "".join(cer_chars_th(normalized)) == normalized


# --------------------------------------------------------------------------
# べき等性 (2回適用しても結果が変わらない) — 両フラグとも必須
# --------------------------------------------------------------------------


IDEMPOTENCE_SAMPLES = [
    "วันนี้มีคนยี่สิบเอ็ดคน มาที่ศูนย์การค้า",
    "ห้ามเข้า เขาสามารถนั่งบนเก้าอี้ได้",
    "ราคา ๓๓,๐๐๐ บาท หรือสามพันห้าร้อยบาท",
    "เร็วๆ นะครับ ๑๒๓",
    "ＡＢＣ１２３ 33,000",
    "สายพันธุ์ใหม่ เรียบร้อยแล้ว มียี่สิบยี่ห้อ",  # ブロックリスト拡充+バックオフ経路
    "สามีของเธอเป็นสิบเอกในกองพัน",              # 構造ガード+語末数詞綴りクラス
]


class TestIdempotence:
    def test_idempotence_default_mode(self):
        for s in IDEMPOTENCE_SAMPLES:
            once = normalize_th(s)
            twice = normalize_th(once)
            assert once == twice, f"idempotence failed for {s!r}: {once!r} != {twice!r}"

    def test_idempotence_strip_all_whitespace_mode(self):
        for s in IDEMPOTENCE_SAMPLES:
            once = normalize_th(s, strip_all_whitespace_for_cer=True)
            twice = normalize_th(once, strip_all_whitespace_for_cer=True)
            assert once == twice, f"idempotence failed for {s!r}: {once!r} != {twice!r}"
