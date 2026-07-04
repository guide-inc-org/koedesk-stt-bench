"""
ポルトガル語テキスト正規化 (PREREGISTRATION §5 の実装)。

パイプライン:
  ステップ1-5 (`_normalize_steps_1_to_5`, 全言語共通の一般規則をポルトガル語向けに実装):
    1. Unicode NFKC 正規化
    2. ケースフォールディング
    3. 句読点・記号除去 (Unicode category P*/S*)。ただし語中アポストロフィ
       (d'água 等) は保持し、’→' に標準化する (§5 ステップ3 の例外)
    4. 空白の圧縮
    5. 数値等価化: 綴り数詞(基数・序数)→数字、桁区切り除去、
       範囲のハイフンはトークン境界化 (§5.5)
  ステップ6 (§5.6, `normalize_pt`):
    ピン留めされた Whisper 公式 BasicTextNormalizer (vendor/whisper_normalizers)
    をステップ1-5の出力の上に適用する。HF Open ASR Leaderboard との比較可能性
    のため。**remove_diacritics はデフォルト (False) を使う**: ダイアクリティクス
    (ã/õ/ç/é 等) の除去は転写内容の同一性判定を歪める (avó と avo は別語) ため
    保持する。HF leaderboard の BasicTextNormalizer 利用もデフォルト設定であり、
    この選択は同 leaderboard との互換性も保つ。
  最終ステップ (冪等性のためのクリーンアップ):
    ステップ3の「P*/S* 除去 (語中アポストロフィ・数字間小数点は例外)」の
    不変条件を最終出力に再適用する (en.py と同じパターン)。

## ステップ順序に関する既知の調整 (§5.5 桁区切りとの整合)

en.py と同じ理由 (同ファイル参照): 桁区切り・小数点の処理だけはステップ3の
一般句読点除去より前に「トークン境界を作らず」行う。

## 桁区切り・小数点の扱い (§5.5、ポルトガル語の慣習行)

- **千区切り**: ポルトガル語は `.` が千区切り。「数字に挟まれた `.` で、直後が
  ちょうど3桁の数字グループ」の場合のみ削除する ("33.000"→"33000")。
- **小数点**: ポルトガル語は `,` が小数点。数字に挟まれた `,` は `.` に正規化し、
  数字間の `.` はステップ3の除去から保護して1トークンに保つ
  ("3,14"→"3.14")。処理順は「小数カンマ→`.` 変換」→「千区切り `.` 削除」
  ("33.000,50"→"33000.50")。
- **宣言済みの衝突クラス**: de.py と同じく、小数部がちょうど3桁の小数
  ("1,000") は整数表記 ("1.000"→"1000") と衝突する。ref/hyp 双方に同一規則が
  適用される決定論的な宣言済み測定ノイズとして許容する。

## §5.5 綴り数詞→数字 (基数・序数、整数 0–99,999)

ポルトガル語の数詞は "e" 連結のトークン列 ("vinte e um"=21,
"cento e vinte e três"=123) なので、トークン列パーサで最長一致の数詞列を
検出して合成する。合成規則 (test_pt.py で検証):
  - 0-19: 単一語 (zero..dezenove、伯 dezesseis/欧 dezasseis 等の変種を含む)
  - 20-99: <10の位> [e <1の位>] (vinte e um=21)。"e" は数詞の位が正しく
    下がる場合のみ数詞列として消費する ("dois e três" は融合しない)
  - 100-999: cem / cento [e 0-99] / Xcentos(as) [e 0-99]
    (cento e vinte e três=123, duzentos e trinta=230, cento e um=101)。
    cento/Xcentos の余り位置は数詞列の内部なので um/uma も数詞として参加する
    ("cento e um"=101。単独の um/uma は曖昧クラスのまま不変換。
    検収で確定したバグの修正)
  - 1,000-99,999: [係数] mil [e] [0-999] (trinta e três mil e
    quinhentos=33500, mil novecentos e oitenta e quatro=1984)。mil の
    余り位置でも um/uma は数詞として参加する ("mil e um"=1001)。
    **範囲超過ガードは原子的**: run 全体をパースした上で結果が 99,999 を
    超える場合は run 全体を不変換で残す (スケール語の先読みで係数だけを
    部分確定しない。"cem mil" が "100 1000" に割れる部分変換は禁止 —
    "cem mil"/"duzentos mil" はそのまま残る。検収で確定したバグの修正)
序数 (primeiro/terceiro/décimo/vigésimo 等、"décimo primeiro"=11 の2語合成を
含む) も裸の数字に変換する (§5.5 en: twentieth→20th→20 と同じ扱い)。
序数10の位の直後に曖昧クラスの序数語 (segundo/segunda・quarto/quarta・
quinta・sexta とその複数形) が続く場合 ("décimo quarto"=14番目/「10番目の
部屋」の両義) は、**run 全体を不変換で残す** (部分変換禁止=全か無かの
一貫適用。両論検討: "décimo quarto"→14 と変換する案は数値文脈による
曖昧性解消だが、「o décimo quarto (10番目の部屋)」等の実在読みを壊す。
旧挙動の "10 quarto" 型混合出力は部分変換であり、run 原子性の原則—範囲超過
ガードや vi/ru の全か無か規則—と非一貫なので廃止。検収F8の修正)。
数字+序数標識のトークン ("20º"/"20ª" は NFKC で "20o"/"20a" になる) も
最後に接尾辞を剥がして裸の数字にする。

## 曖昧クラス (§5.5「ambiguous classes are left untouched」、test_pt.py で列挙)

冠詞・曜日・一般名詞と数詞を文脈判定しない=決定論を維持するため、以下は
**変換しない**:
  - "um"/"uma" 単独 (不定冠詞/数詞の両義。ポルトガル語は冠詞と数詞1が完全
    同形)。数詞列の内部 ("vinte e um", "trinta e uma"、および cento/mil の
    余り位置 "cento e um"/"mil e um") では数詞としてのみ現れるため変換に
    参加する
  - "segundo"/"segunda" (序数2と「秒」「〜によれば(前置詞)」「月曜
    segunda(-feira)」が同形)
  - "quarto"/"quarta" (序数4と「部屋」「水曜 quarta(-feira)」が同形)
  - "quinta" (序数5女性形と「木曜 quinta(-feira)」「農園」が同形。
    男性形 "quinto" は無曖昧なので変換する)
  - "sexta" (序数6女性形と「金曜 sexta(-feira)」が同形。男性形 "sexto" は
    変換する)
曜日と衝突する女性形だけを除外し男性形は変換する非対称は、同形異義の
実在に基づく意図的な線引きである (test_pt.py で両側を列挙)。

## §5.6 BasicTextNormalizer とアポストロフィ/小数点の保護

de.py と同じ設計判断 (同ファイル参照): 凍結済み §5 ステップ3 の明示例外
(語中アポストロフィ保持) と本実装の小数点保持を、Private Use Area の
プレースホルダで Basic 適用をまたいで保護する。

意図的差分 (HF 互換の既知乖離、検収F6): 生の BasicTextNormalizer は
(…)/[…]/<…> の括弧内テキストを削除するが、本実装ではステップ3が括弧文字を
先に空白化するため、§5.6 適用時点で括弧が存在せずこの削除は発火しない。
挙動は変更しない (en.py と共通の構造: ステップ1-5が先行するパイプライン設計の
帰結であり、括弧内容も転写テキストとして対称に採点される)。
"""
from __future__ import annotations

import re
import unicodedata

from .vendor.whisper_normalizers.basic import BasicTextNormalizer

# プレースホルダ (Private Use Area、de.py と同じ方式)。
_APOS_PLACEHOLDER = "\ue000"
_DECIMAL_PLACEHOLDER = "\ue001"

_WHITESPACE_RE = re.compile(r"\s+")
_WORD_INTERNAL_APOS_RE = re.compile(r"(?<=\w)'(?=\w)")
_DIGIT_INTERNAL_DOT_RE = re.compile(r"(?<=\d)\.(?=\d)")
_DECIMAL_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")
_THOUSANDS_DOT_RE = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")
# 数字トークンの序数標識 (NFKC 後: 20º→20o, 20ª→20a, 複数形 20os/20as)
_DIGIT_ORDINAL_SUFFIX_RE = re.compile(r"\b(\d+)[oa]s?\b")

_basic_normalizer = BasicTextNormalizer()  # remove_diacritics=False (デフォルト)


# --- 綴り数詞の語彙 (casefold 後の表記。無アクセント変種も受理) --------------------

def _with_unaccented_variants(d: dict[str, int]) -> dict[str, int]:
    """ê 等を落とした無アクセント表記も同じ値で受理できるよう語彙を複製する。"""
    out = dict(d)
    for word, val in d.items():
        plain = "".join(
            c
            for c in unicodedata.normalize("NFD", word)
            if unicodedata.category(c) != "Mn"
        )
        out.setdefault(plain, val)
    return out


_PT_ZERO = {"zero": 0}
_PT_UNITS = _with_unaccented_variants({
    "dois": 2, "duas": 2, "três": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9,
})
# "e" の後ろ・数詞列内部でのみ 1 と読む形 (単独では曖昧クラス)。
_PT_UNITS_AFTER_E = dict(_PT_UNITS, um=1, uma=1)
_PT_TEENS = {
    "dez": 10, "onze": 11, "doze": 12, "treze": 13,
    "catorze": 14, "quatorze": 14, "quinze": 15,
    "dezesseis": 16, "dezasseis": 16,
    "dezessete": 17, "dezassete": 17,
    "dezoito": 18,
    "dezenove": 19, "dezanove": 19,
}
_PT_TENS = {
    "vinte": 20, "trinta": 30, "quarenta": 40, "cinquenta": 50,
    "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90,
}
_PT_HUNDREDS = {
    "cem": 100, "cento": 100,
    "duzentos": 200, "duzentas": 200,
    "trezentos": 300, "trezentas": 300,
    "quatrocentos": 400, "quatrocentas": 400,
    "quinhentos": 500, "quinhentas": 500,
    "seiscentos": 600, "seiscentas": 600,
    "setecentos": 700, "setecentas": 700,
    "oitocentos": 800, "oitocentas": 800,
    "novecentos": 900, "novecentas": 900,
}


def _gender_number_forms(stem: str, value: int) -> dict[str, int]:
    """序数語幹 (末尾母音抜き) から o/a/os/as の4形を生成する。"""
    return {stem + suffix: value for suffix in ("o", "a", "os", "as")}


# 序数の1の位相当 (単独および序数10の位の後続として使う)。
# segundo/segunda・quarto/quarta・quinta・sexta は曖昧クラスとして意図的に除外
# (モジュールdocstring参照)。
_PT_ORDINAL_UNITS = _with_unaccented_variants({
    **_gender_number_forms("primeir", 1),
    **_gender_number_forms("terceir", 3),
    "quinto": 5, "quintos": 5,   # quinta/quintas は曜日「木曜」と同形のため除外
    "sexto": 6, "sextos": 6,     # sexta/sextas は曜日「金曜」と同形のため除外
    **_gender_number_forms("sétim", 7),
    **_gender_number_forms("oitav", 8),
    **_gender_number_forms("non", 9),
})
# 序数の10の位以上 (1の位序数を後続できる: "décimo primeiro"=11)。
_PT_ORDINAL_TENS = _with_unaccented_variants({
    **_gender_number_forms("décim", 10),
    **_gender_number_forms("vigésim", 20),
    **_gender_number_forms("trigésim", 30),
    **_gender_number_forms("quadragésim", 40),
    **_gender_number_forms("quinquagésim", 50),
    **_gender_number_forms("sexagésim", 60),
    **_gender_number_forms("septuagésim", 70),
    **_gender_number_forms("setuagésim", 70),
    **_gender_number_forms("octogésim", 80),
    **_gender_number_forms("nonagésim", 90),
    **_gender_number_forms("centésim", 100),
    **_gender_number_forms("milésim", 1000),
})


# 序数10の位の直後に続くと run 全体を不変換にする曖昧クラスの序数語
# ("décimo quarto" 型。モジュールdocstring §5.5 参照)。
_PT_AMBIGUOUS_ORDINAL_UNITS = frozenset({
    "segundo", "segunda", "segundos", "segundas",
    "quarto", "quarta", "quartos", "quartas",
    "quinta", "quintas", "sexta", "sextas",
})


def _pt_parse_0_99(
    tokens: list[str], i: int, in_remainder: bool = False
) -> tuple[int, int] | None:
    """0-99 の数詞列。(値, 消費トークン数) を返す。

    in_remainder: cento/mil の余り位置 (=数詞列の内部) を解析中かどうか。
    余り位置では um/uma も数詞として受理する ("cento e um"=101)。
    単独の um/uma (冠詞との曖昧クラス) はここを通らないため不変換のまま。
    """
    n = len(tokens)
    t = tokens[i]
    if t in _PT_ZERO:
        return 0, 1
    if t in _PT_TEENS:
        return _PT_TEENS[t], 1
    if t in _PT_TENS:
        base = _PT_TENS[t]
        # <10の位> e <1の位> のみ "e" を数詞列として消費する。
        if (
            i + 2 < n
            and tokens[i + 1] == "e"
            and tokens[i + 2] in _PT_UNITS_AFTER_E
        ):
            return base + _PT_UNITS_AFTER_E[tokens[i + 2]], 3
        return base, 1
    if t in _PT_UNITS:  # um/uma は含まれない (曖昧クラス)
        return _PT_UNITS[t], 1
    if in_remainder and t in _PT_UNITS_AFTER_E:
        # 余り位置は数詞列の内部: um/uma を数詞として受理する。
        return _PT_UNITS_AFTER_E[t], 1
    return None


def _pt_parse_1_999(
    tokens: list[str], i: int, in_remainder: bool = False
) -> tuple[int, int] | None:
    """100の位 [e 0-99]、または 0-99。

    in_remainder は 0-99 へのフォールバック時にそのまま伝播する
    (mil の余り位置から呼ばれた場合)。cento/Xcentos の余りは常に数詞列内部。
    """
    n = len(tokens)
    t = tokens[i]
    if t in _PT_HUNDREDS:
        value, consumed = _PT_HUNDREDS[t], 1
        # "cem" は後続なし。"cento"/"Xcentos" は "e" を挟んで 0-99 を後続できる。
        if (
            t != "cem"
            and i + 2 < n
            and tokens[i + 1] == "e"
        ):
            rest = _pt_parse_0_99(tokens, i + 2, in_remainder=True)
            if rest is not None:
                return value + rest[0], consumed + 1 + rest[1]
        return value, consumed
    return _pt_parse_0_99(tokens, i, in_remainder)


def _pt_parse_ordinal_at(tokens: list[str], i: int) -> tuple[int | None, int]:
    """序数列 ("décimo primeiro"=11 の2語合成を含む)。

    戻り値の規約は _pt_parse_number_at と同じ:
    (None, 2) は「序数10の位+曖昧クラス序数語」の run 全体不変換
    ("décimo quarto" 型、全か無か)、(None, 0) は非序数。
    """
    t = tokens[i]
    if t in _PT_ORDINAL_TENS:
        value, consumed = _PT_ORDINAL_TENS[t], 1
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if nxt in _PT_ORDINAL_UNITS:
                return value + _PT_ORDINAL_UNITS[nxt], 2
            if nxt in _PT_AMBIGUOUS_ORDINAL_UNITS:
                # "décimo quarto" (14番目/10番目の部屋) は両義 → run 全体不変換
                # (部分変換 "10 quarto" を生まない。モジュールdocstring参照)。
                return None, 2
        return value, consumed
    if t in _PT_ORDINAL_UNITS:
        return _PT_ORDINAL_UNITS[t], 1
    return None, 0


def _pt_parse_number_at(tokens: list[str], i: int) -> tuple[int | None, int]:
    """位置 i から始まる最長の数詞列を (値, 消費トークン数) で返す。

    戻り値の規約 (ru.py の _parse_number_run と同型):
      (値, 消費 > 0)    → 変換して消費する。
      (None, 消費 > 0)  → 数詞 run ではあるが不変換で残す (範囲超過 /
                          曖昧クラス序数語との複合)。呼び出し側は run 全体を
                          そのまま出力して読み飛ばす (原子的ガード)。
      (None, 0)         → 数詞列ではない。
    """
    n = len(tokens)
    sub = _pt_parse_1_999(tokens, i)
    if sub is not None:
        value, consumed = sub
        if i + consumed < n and tokens[i + consumed] == "mil":
            # スケール語は範囲チェックの前に run へ取り込む (先読みで係数だけ
            # 部分確定しない)。範囲超過なら余りまで含めた run 全体を不変換。
            total = value * 1000
            consumed += 1
            rest_i = i + consumed
            # "mil e quinhentos" のように "e" を挟む形と挟まない形の両方を受理。
            skip_e = 1 if rest_i < n and tokens[rest_i] == "e" else 0
            if rest_i + skip_e < n:
                rest = _pt_parse_1_999(tokens, rest_i + skip_e, in_remainder=True)
                if rest is not None:
                    total += rest[0]
                    consumed += skip_e + rest[1]
            if total > 99999:
                return None, consumed
            return total, consumed
        return value, consumed
    if tokens[i] == "mil":
        total, consumed = 1000, 1
        rest_i = i + 1
        skip_e = 1 if rest_i < n and tokens[rest_i] == "e" else 0
        if rest_i + skip_e < n:
            rest = _pt_parse_1_999(tokens, rest_i + skip_e, in_remainder=True)
            if rest is not None:
                total += rest[0]
                consumed += skip_e + rest[1]
        return total, consumed
    return _pt_parse_ordinal_at(tokens, i)


def _convert_spelled_numbers(text: str) -> str:
    """§5.5: 綴り数詞列 (基数・序数) を数字に変換する。"""
    tokens = text.split(" ")
    out: list[str] = []
    i = 0
    while i < len(tokens):
        value, consumed = _pt_parse_number_at(tokens, i)
        if consumed == 0:
            out.append(tokens[i])
            i += 1
        elif value is None:
            # 不変換 run (範囲超過 / 曖昧序数複合): 全体をそのまま残す。
            out.extend(tokens[i : i + consumed])
            i += consumed
        else:
            out.append(str(value))
            i += consumed
    return " ".join(out)


def _collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _strip_symbols_keep_protected(text: str) -> str:
    """§5 ステップ3の句読点・記号除去 (P*/S*)。

    例外として語中アポストロフィ (§5 ステップ3 明記) と、数字に挟まれた
    小数点 "." (本実装の決定、モジュールdocstring参照) を保持する。
    """
    text = text.replace("’", "'")
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = _DIGIT_INTERNAL_DOT_RE.sub(_DECIMAL_PLACEHOLDER, text)
    text = "".join(
        " " if unicodedata.category(ch)[0] in ("P", "S") else ch for ch in text
    )
    return text.replace(_APOS_PLACEHOLDER, "'").replace(_DECIMAL_PLACEHOLDER, ".")


def _normalize_steps_1_to_5(text: str) -> str:
    """PREREGISTRATION §5 ステップ1-5 (ポルトガル語向け実装)。"""
    # 1. Unicode NFKC (º→o / ª→a を含む)
    text = unicodedata.normalize("NFKC", text)

    # 2. ケースフォールディング
    text = text.casefold()

    # 5 (前倒し実行, モジュールdocstring参照): 小数カンマ→"." → "." 千区切り削除。
    text = text.replace("’", "'")
    text = _DECIMAL_COMMA_RE.sub(".", text)
    text = _THOUSANDS_DOT_RE.sub("", text)

    # 3. 句読点・記号除去 (P*/S*、語中アポストロフィ・数字間小数点は例外)
    text = _strip_symbols_keep_protected(text)

    # 4. 空白圧縮
    text = _collapse_whitespace(text)

    # 5. 綴り数詞(基数・序数)→数字、数字トークンの序数標識剥がし (20o→20)
    text = _convert_spelled_numbers(text)
    text = _DIGIT_ORDINAL_SUFFIX_RE.sub(r"\1", text)
    text = _collapse_whitespace(text)

    return text


def normalize_pt(text: str) -> str:
    """PREREGISTRATION §5 (ステップ1-5 + §5.6 Basic normalizer) を適用する。"""
    text = _normalize_steps_1_to_5(text)

    # §5.6: ピン留めされた Whisper BasicTextNormalizer (remove_diacritics=False)。
    # 語中アポストロフィ・数字間小数点はプレースホルダで保護する。
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = _DIGIT_INTERNAL_DOT_RE.sub(_DECIMAL_PLACEHOLDER, text)
    text = _basic_normalizer(text)
    text = text.replace(_APOS_PLACEHOLDER, "'").replace(_DECIMAL_PLACEHOLDER, ".")

    # 冪等性を保証する最終クリーンアップ (ステップ3の不変条件の再適用)。
    text = _strip_symbols_keep_protected(text)
    text = _collapse_whitespace(text)

    return text


def tokenize_pt(text: str) -> list[str]:
    """正規化済みテキストを空白分割する (WER 用)。"""
    normalized = normalize_pt(text)
    if not normalized:
        return []
    return normalized.split(" ")
