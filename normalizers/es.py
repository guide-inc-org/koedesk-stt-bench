"""
スペイン語テキスト正規化 (PREREGISTRATION §5 の実装)。

パイプライン:
  ステップ1-5 (`_normalize_steps_1_to_5`, 全言語共通の一般規則をスペイン語向けに実装):
    1. Unicode NFKC 正規化
    2. ケースフォールディング
    3. 句読点・記号除去 (Unicode category P*/S*、¿/¡ を含む)。ただし
       語中アポストロフィは保持し、’→' に標準化する (§5 ステップ3 の例外)
    4. 空白の圧縮
    5. 数値等価化: 綴り数詞(基数・序数)→数字、桁区切り除去、
       範囲のハイフンはトークン境界化 (§5.5)
  ステップ6 (§5.6, `normalize_es`):
    ピン留めされた Whisper 公式 BasicTextNormalizer (vendor/whisper_normalizers)
    をステップ1-5の出力の上に適用する。HF Open ASR Leaderboard との比較可能性
    のため。**remove_diacritics はデフォルト (False) を使う**: ダイアクリティクス
    (á/é/ñ 等) の除去は転写内容の同一性判定を歪める (año と ano は別語) ため
    保持する。HF leaderboard の BasicTextNormalizer 利用もデフォルト設定であり、
    この選択は同 leaderboard との互換性も保つ。
  最終ステップ (冪等性のためのクリーンアップ):
    ステップ3の「P*/S* 除去 (語中アポストロフィ・数字間小数点は例外)」の
    不変条件を最終出力に再適用する (en.py と同じパターン)。

## ステップ順序に関する既知の調整 (§5.5 桁区切りとの整合)

en.py と同じ理由 (同ファイル参照): 桁区切り・小数点の処理だけはステップ3の
一般句読点除去より前に「トークン境界を作らず」行う。

## 桁区切り・小数点の扱い (§5.5、スペイン語の慣習行)

- **千区切り**: スペイン語は `.` が千区切り。「数字に挟まれた `.` で、直後が
  ちょうど3桁の数字グループ」の場合のみ削除する ("33.000"→"33000")。
  「ちょうど3桁」条件により "3.14" のような非・桁区切りパターンを融合しない。
- **小数点**: スペイン語は `,` が小数点。数字に挟まれた `,` は `.` に正規化し、
  数字間の `.` はステップ3の除去から保護して1トークンに保つ
  ("3,14"→"3.14")。処理順は「小数カンマ→`.` 変換」→「千区切り `.` 削除」
  ("33.000,50"→"33000.50")。
- **宣言済みの衝突クラス**: de.py と同じく、"1,000" (小数) は変換後に千区切り
  規則が発火して "1000" となり "1.000" (千区切り) と同値になる。小数部が
  ちょうど3桁の小数は整数表記と衝突するが、ref/hyp 双方に同一規則が適用される
  決定論的な宣言済み測定ノイズとして許容する。

## §5.5 綴り数詞→数字 (基数・序数、整数 0–99,999)

スペイン語の数詞は複合語 (veintiuno=21) とトークン列 ("treinta y uno"=31、
"y" は10の位と1の位の間のみ) の混合なので、トークン列パーサで最長一致の
数詞列を検出して合成する。合成規則 (test_es.py で検証):
  - 0-29: 単一語 (cero..veintinueve、veintiún/veintiuna 変種を含む)
  - 30-99: <10の位> [y <1の位>] (treinta y uno=31)。"y" は10の位の直後に
    1の位が続く場合のみ数詞列として消費する ("cinco y seis" は融合しない)
  - 100-999: cien / ciento [+0-99] / Xcientos(as) [+0-99] (doscientos
    treinta y cuatro=234, ciento uno=101)。ciento の余り位置は数詞列の内部
    なので un/una/ún も数詞として参加する ("ciento un libros"=101 libros。
    単独の un/una は曖昧クラスのまま不変換。検収で確定したバグの修正)
  - 1,000-99,999: [係数] mil [+0-999] (treinta y tres mil quinientos
    =33500)。mil の余り位置でも un/una は数詞として参加する ("mil un"=1001)。
    **範囲超過ガードは原子的**: run 全体をパースした上で結果が 99,999 を
    超える場合は run 全体を不変換で残す (スケール語の先読みで係数だけを
    部分確定しない。"cien mil" が "100 1000" に割れる部分変換は禁止 —
    "cien mil"/"doscientos mil" はそのまま残る。検収で確定したバグの修正)
序数 (primero/tercero/décimo/vigésimo 等、"vigésimo primero"=21 の2語合成を
含む) も裸の数字に変換する (§5.5 en: twentieth→20th→20 と同じ扱い)。
序数10の位の直後に曖昧クラスの序数語 (segundo/segunda・cuarto/cuarta とその
複数形) が続く場合 ("décimo cuarto"=14番目/「10番目の部屋」の両義) は、
**run 全体を不変換で残す** (部分変換禁止=全か無かの一貫適用。両論検討:
"décimo cuarto"→14 と変換する案は linh/lẻ 式の「数値文脈による曖昧性解消」
だが、「el décimo cuarto (10番目の部屋)」の実在読みを壊す。旧挙動の
"10 cuarto" 型混合出力は部分変換であり、run 原子性の原則—範囲超過ガードや
vi/ru の全か無か規則—と非一貫なので廃止。検収F8の修正)。
数字+序数標識のトークン ("20º"/"20ª" は NFKC で "20o"/"20a" になる) も
最後に接尾辞を剥がして裸の数字にする (温度の "20o" が巻き込まれ得るのは
宣言済みノイズ)。

## 曖昧クラス (§5.5「ambiguous classes are left untouched」、test_es.py で列挙)

冠詞と数詞を文脈判定しない=決定論を維持するため、以下は**変換しない**:
  - "un"/"una" 単独 (不定冠詞/数詞の両義)。数詞列の内部 ("treinta y un",
    "veintiuna"、および ciento/mil の余り位置 "ciento un"/"mil un") では
    数詞としてのみ現れるため変換に参加する
  - "segundo"/"segunda" (序数2と名詞「秒」・「副〜」が同形の同形異義)
  - "cuarto"/"cuarta" (序数4と名詞「部屋」「4分の1」が同形の同形異義)
一方 "uno" は数詞読みが支配的 (冠詞は "un" であり "uno" ではない。
不定代名詞用法は存在するが頻度で劣る) なので、両論検討の上**変換する**
ことを採用した。変換しないと ref/hyp の "1"⇔"uno" 等価が壊れて §5.5 の
目的を損なう (宣言済みの決定論的選択)。

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
_APOS_PLACEHOLDER = ""
_DECIMAL_PLACEHOLDER = ""

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
    """á 等を落とした無アクセント表記も同じ値で受理できるよう語彙を複製する。

    注: ñ は NFD でも n+チルダに分解されるため "veintiún"→"veintiun" のような
    アクセント欠落変種の受理が目的 (ñ→n の同一視はここでは起こさない...
    と言いたいところだが NFD+Mn除去は ñ→n も生む。数詞語彙に ñ を含む語は
    ないため実害はない)。
    """
    out = dict(d)
    for word, val in d.items():
        plain = "".join(
            c
            for c in unicodedata.normalize("NFD", word)
            if unicodedata.category(c) != "Mn"
        )
        out.setdefault(plain, val)
    return out


_ES_ZERO = {"cero": 0}
_ES_UNITS = {
    "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9,
}
# "y" の後ろ・数詞列内部でのみ 1 と読む形 (単独では曖昧クラス)。
_ES_UNITS_AFTER_Y = _with_unaccented_variants(
    dict(_ES_UNITS, un=1, una=1, ún=1)
)
_ES_TEENS_AND_TWENTIES = _with_unaccented_variants({
    "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14,
    "quince": 15, "dieciséis": 16, "diecisiete": 17, "dieciocho": 18,
    "diecinueve": 19,
    "veinte": 20, "veintiuno": 21, "veintiún": 21, "veintiuna": 21,
    "veintidós": 22, "veintitrés": 23, "veinticuatro": 24, "veinticinco": 25,
    "veintiséis": 26, "veintisiete": 27, "veintiocho": 28, "veintinueve": 29,
})
_ES_TENS = {
    "treinta": 30, "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
    "setenta": 70, "ochenta": 80, "noventa": 90,
}
_ES_HUNDREDS = {
    "cien": 100, "ciento": 100,
    "doscientos": 200, "doscientas": 200,
    "trescientos": 300, "trescientas": 300,
    "cuatrocientos": 400, "cuatrocientas": 400,
    "quinientos": 500, "quinientas": 500,
    "seiscientos": 600, "seiscientas": 600,
    "setecientos": 700, "setecientas": 700,
    "ochocientos": 800, "ochocientas": 800,
    "novecientos": 900, "novecientas": 900,
}


def _gender_number_forms(stem: str, value: int) -> dict[str, int]:
    """序数語幹 (末尾母音抜き) から o/a/os/as の4形を生成する。"""
    return {stem + suffix: value for suffix in ("o", "a", "os", "as")}


# 序数の1の位相当 (単独および序数10の位の後続として使う)。
# segundo/segunda (秒)・cuarto/cuarta (部屋) は曖昧クラスとして意図的に除外。
_ES_ORDINAL_UNITS = _with_unaccented_variants({
    "primero": 1, "primera": 1, "primeros": 1, "primeras": 1, "primer": 1,
    "tercero": 3, "tercera": 3, "terceros": 3, "terceras": 3, "tercer": 3,
    **_gender_number_forms("quint", 5),
    **_gender_number_forms("sext", 6),
    **_gender_number_forms("séptim", 7),
    **_gender_number_forms("octav", 8),
    **_gender_number_forms("noven", 9),
})
# 序数の10の位以上 (1の位序数を後続できる: "vigésimo primero"=21)。
_ES_ORDINAL_TENS = _with_unaccented_variants({
    **_gender_number_forms("décim", 10),
    **_gender_number_forms("vigésim", 20),
    **_gender_number_forms("trigésim", 30),
    **_gender_number_forms("cuadragésim", 40),
    **_gender_number_forms("quincuagésim", 50),
    **_gender_number_forms("sexagésim", 60),
    **_gender_number_forms("septuagésim", 70),
    **_gender_number_forms("octogésim", 80),
    **_gender_number_forms("nonagésim", 90),
    **_gender_number_forms("centésim", 100),
    **_gender_number_forms("milésim", 1000),
})
# 単独でのみ使う序数 (合成に参加しない)。
_ES_ORDINAL_STANDALONE = _with_unaccented_variants({
    **_gender_number_forms("undécim", 11),
    **_gender_number_forms("duodécim", 12),
})


# 序数10の位の直後に続くと run 全体を不変換にする曖昧クラスの序数語
# ("décimo cuarto" 型。モジュールdocstring §5.5 参照)。
_ES_AMBIGUOUS_ORDINAL_UNITS = frozenset({
    "segundo", "segunda", "segundos", "segundas",
    "cuarto", "cuarta", "cuartos", "cuartas",
})


def _es_parse_0_99(
    tokens: list[str], i: int, in_remainder: bool = False
) -> tuple[int, int] | None:
    """0-99 の数詞列。(値, 消費トークン数) を返す。

    in_remainder: ciento/mil の余り位置 (=数詞列の内部) を解析中かどうか。
    余り位置では un/una/ún も数詞として受理する ("ciento un"=101)。
    単独の un/una (冠詞との曖昧クラス) はここを通らないため不変換のまま。
    """
    n = len(tokens)
    t = tokens[i]
    if t in _ES_ZERO:
        return 0, 1
    if t in _ES_TEENS_AND_TWENTIES:
        return _ES_TEENS_AND_TWENTIES[t], 1
    if t in _ES_TENS:
        base = _ES_TENS[t]
        # <10の位> y <1の位> のみ "y" を数詞列として消費する。
        if (
            i + 2 < n
            and tokens[i + 1] == "y"
            and tokens[i + 2] in _ES_UNITS_AFTER_Y
        ):
            return base + _ES_UNITS_AFTER_Y[tokens[i + 2]], 3
        return base, 1
    if t in _ES_UNITS:  # uno は変換対象、un/una は含まれない (曖昧クラス)
        return _ES_UNITS[t], 1
    if in_remainder and t in _ES_UNITS_AFTER_Y:
        # 余り位置は数詞列の内部: un/una/ún を数詞として受理する。
        return _ES_UNITS_AFTER_Y[t], 1
    return None


def _es_parse_1_999(
    tokens: list[str], i: int, in_remainder: bool = False
) -> tuple[int, int] | None:
    """100の位 + 0-99、または 0-99。

    in_remainder は 0-99 へのフォールバック時にそのまま伝播する
    (mil の余り位置から呼ばれた場合)。ciento 系の余りは常に数詞列内部。
    """
    n = len(tokens)
    t = tokens[i]
    if t in _ES_HUNDREDS:
        value, consumed = _ES_HUNDREDS[t], 1
        # "cien" は後続なし ("ciento cinco"=105, "cien"=100)。
        if t != "cien" and i + 1 < n:
            rest = _es_parse_0_99(tokens, i + 1, in_remainder=True)
            if rest is not None:
                return value + rest[0], consumed + rest[1]
        return value, consumed
    return _es_parse_0_99(tokens, i, in_remainder)


def _es_parse_ordinal_at(tokens: list[str], i: int) -> tuple[int | None, int]:
    """序数列 ("vigésimo primero"=21 の2語合成を含む)。

    戻り値の規約は _es_parse_number_at と同じ:
    (None, 2) は「序数10の位+曖昧クラス序数語」の run 全体不変換
    ("décimo cuarto" 型、全か無か)、(None, 0) は非序数。
    """
    t = tokens[i]
    if t in _ES_ORDINAL_TENS:
        value, consumed = _ES_ORDINAL_TENS[t], 1
        if i + 1 < len(tokens):
            nxt = tokens[i + 1]
            if nxt in _ES_ORDINAL_UNITS:
                return value + _ES_ORDINAL_UNITS[nxt], 2
            if nxt in _ES_AMBIGUOUS_ORDINAL_UNITS:
                # "décimo cuarto" (14番目/10番目の部屋) は両義 → run 全体不変換
                # (部分変換 "10 cuarto" を生まない。モジュールdocstring参照)。
                return None, 2
        return value, consumed
    if t in _ES_ORDINAL_UNITS:
        return _ES_ORDINAL_UNITS[t], 1
    if t in _ES_ORDINAL_STANDALONE:
        return _ES_ORDINAL_STANDALONE[t], 1
    return None, 0


def _es_parse_number_at(tokens: list[str], i: int) -> tuple[int | None, int]:
    """位置 i から始まる最長の数詞列を (値, 消費トークン数) で返す。

    戻り値の規約 (ru.py の _parse_number_run と同型):
      (値, 消費 > 0)    → 変換して消費する。
      (None, 消費 > 0)  → 数詞 run ではあるが不変換で残す (範囲超過 /
                          曖昧クラス序数語との複合)。呼び出し側は run 全体を
                          そのまま出力して読み飛ばす (原子的ガード)。
      (None, 0)         → 数詞列ではない。
    """
    n = len(tokens)
    sub = _es_parse_1_999(tokens, i)
    if sub is not None:
        value, consumed = sub
        if i + consumed < n and tokens[i + consumed] == "mil":
            # スケール語は範囲チェックの前に run へ取り込む (先読みで係数だけ
            # 部分確定しない)。範囲超過なら余りまで含めた run 全体を不変換。
            total = value * 1000
            consumed += 1
            if i + consumed < n:
                rest = _es_parse_1_999(tokens, i + consumed, in_remainder=True)
                if rest is not None:
                    total += rest[0]
                    consumed += rest[1]
            if total > 99999:
                return None, consumed
            return total, consumed
        return value, consumed
    if tokens[i] == "mil":
        total, consumed = 1000, 1
        if i + 1 < n:
            rest = _es_parse_1_999(tokens, i + 1, in_remainder=True)
            if rest is not None:
                total += rest[0]
                consumed += rest[1]
        return total, consumed
    return _es_parse_ordinal_at(tokens, i)


def _convert_spelled_numbers(text: str) -> str:
    """§5.5: 綴り数詞列 (基数・序数) を数字に変換する。"""
    tokens = text.split(" ")
    out: list[str] = []
    i = 0
    while i < len(tokens):
        value, consumed = _es_parse_number_at(tokens, i)
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
    """PREREGISTRATION §5 ステップ1-5 (スペイン語向け実装)。"""
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


def normalize_es(text: str) -> str:
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


def tokenize_es(text: str) -> list[str]:
    """正規化済みテキストを空白分割する (WER 用)。"""
    normalized = normalize_es(text)
    if not normalized:
        return []
    return normalized.split(" ")
