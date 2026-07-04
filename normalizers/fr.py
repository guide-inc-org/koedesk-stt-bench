"""
フランス語テキスト正規化 (PREREGISTRATION §5 の実装)。

パイプライン:
  ステップ1-5 (`_normalize_steps_1_to_5`, 全言語共通の一般規則をフランス語向けに実装):
    1. Unicode NFKC 正規化
    2. ケースフォールディング
    3. 句読点・記号除去 (Unicode category P*/S*)。ただし語中アポストロフィ
       (l'homme, d'accord, aujourd'hui 等のエリジオン) は保持し、’→' に
       標準化する (§5 ステップ3 の明記された例外。フランス語では特に重要)
    4. 空白の圧縮
    5. 数値等価化: 綴り数詞(基数・序数)→数字、桁区切り除去、
       範囲のハイフンはトークン境界化 (§5.5)
  ステップ6 (§5.6, `normalize_fr`):
    ピン留めされた Whisper 公式 BasicTextNormalizer (vendor/whisper_normalizers)
    をステップ1-5の出力の上に適用する。HF Open ASR Leaderboard との比較可能性
    のため。**remove_diacritics はデフォルト (False) を使う**: ダイアクリティクス
    (é/è/ç/à 等) の除去は転写内容の同一性判定を歪める (côte と cote は別語) ため
    保持する。HF leaderboard の BasicTextNormalizer 利用もデフォルト設定であり、
    この選択は同 leaderboard との互換性も保つ。
  最終ステップ (冪等性のためのクリーンアップ):
    ステップ3の「P*/S* 除去 (語中アポストロフィ・数字間小数点は例外)」の
    不変条件を最終出力に再適用する (en.py と同じパターン)。

## ステップ順序に関する既知の調整 (§5.5 桁区切りとの整合)

en.py と同じ理由 (同ファイル参照): 桁区切り・小数点の処理だけはステップ3の
一般句読点除去より前に「トークン境界を作らず」行う。

## 桁区切り・小数点の扱い (§5.5、フランス語の慣習行)

- **千区切り**: フランス語は空白 (U+00A0 NBSP / U+202F 狭域NBSP を含む) が
  千区切り。NFKC (ステップ1) が NBSP 類を通常スペースへ正規化するので、
  「数字に挟まれたスペース1個で、直後がちょうど3桁の数字グループ」の場合のみ
  削除する ("33 000"→"33000", "1 000 000"→"1000000")。「ちょうど3桁」条件に
  より、数値の単純な列挙 ("25 30" 等) を誤って融合しない。
- **千区切り融合の再適用 (冪等性のため; 検収で確定したバグの修正)**: この融合を
  綴り数詞変換 (ステップ5) より前にしか適用しないと、数詞変換が生成した数字の
  直後に3桁数字が続く入力 ("dix 300"→"10 300") が不動点にならず、2回目の
  normalize で "10300" に変わる (冪等性違反)。両論を検討した:
    (a) 採用: 綴り数詞変換の後 (および最終クリーンアップの後) にも同じ融合を
        再適用し、出力自体を融合規則の不動点にする。宣言済みの桁区切り慣習
        (空白=千区切り) は変えない。
    (b) 不採用: ru 式に「NBSP/狭域NBSP のみを千区切りとする」保守案へ縮める。
        冪等にはなるが、§5.5 の言語別慣習表 (fr は空白が千区切り) の変更に
        あたり、"33 000" (通常スペース) ⇔ "33000" の宣言済み等価性を失う。
  (a) の帰結として、「数字トークン+ちょうど3桁の数字トークン」の並びは
  出所を問わず融合する: "2026, 300"→"2026300"、数詞変換経由の
  "en 2026 trois cents personnes"→"en 2026300 personnes" 型の誤融合も
  起こる (検収F9)。ref/hyp 双方に同一規則が適用される宣言済み測定ノイズ。
- **小数点**: フランス語は `,` が小数点。数字に挟まれた `,` は `.` に正規化し、
  数字間の `.` はステップ3の除去から保護して1トークンに保つ ("3,14"→"3.14")。
- **宣言済みの衝突クラス**: 英語式に `.` 千区切りで書かれた "33.000" は
  フランス語の慣習行では千区切りと解釈されず小数点として保護される
  ("33.000" のまま)。§5.5 の桁区切り表は言語ごとの慣習行を適用すると
  定めているため、これは仕様どおりの決定論的挙動である (測定ノイズとして宣言)。

## §5.5 綴り数詞→数字 (基数・序数、整数 0–99,999)

フランス語の数詞はハイフン連結 ("quatre-vingt-dix") がステップ3で
トークン境界化されるため、**トークン列パーサ**で最長一致の数詞列を検出して
合成する。合成規則 (test_fr.py で検証):
  - vingt/trente/quarante/cinquante(+septante/huitante/octante/nonante の
    ベルギー/スイス変種) + 単位 (vingt-deux=22)、"et un/une" (vingt et un=21)
  - soixante + 10台 (soixante-quinze=75, soixante-dix=70, soixante et onze=71)
  - quatre-vingt(s) + 単位/10台 (quatre-vingt-dix=90, quatre-vingt-treize=93)
  - [係数] cent(s) [+余り] (deux cent trois=203, cent un=101)
  - [係数] mille [+余り] (trente-trois mille=33000, mille et un=1001)。
    **範囲超過ガードは原子的**: run 全体をパースした上で結果が 99,999 を
    超える場合は run 全体を不変換で残す (スケール語の先読みで係数だけを
    部分確定しない。"cent mille" が "100 1000" に割れる部分変換は禁止 —
    "cent mille"/"deux cent mille" はそのまま残る。検収で確定したバグの修正)
序数 ("ième(s)" 語尾 + premier/première、数詞列の終端としての
"vingt et unième"=21、"quatre-vingtième"=80 等) も裸の数字に変換する
(§5.5 en: twentieth→20th→20 と同じ扱い)。cent/mille の余り位置の序数終端は
unième 型 ("deux cent unième"=201) のみ受理し、premier/première は受理しない
(101e の標準形は "cent-unième" であり、"cent premier" は複合序数ではなく
2つの独立した数詞列として扱う)。"quatre vingtièmes" (分数 4/20 の読み) は
序数 quatre-vingtième(s)=80 と同形になるが、ハイフン情報がステップ3で失われる
以上決定論的には区別できず、複合序数読み (80) を採用する (両論検討: 分数読みを
守るには不変換にするしかないが、それは "80ème"⇔"quatre-vingtième" の §5.5
等価を壊す。頻度で勝る序数読みを採用し宣言済みノイズとする)。
数字+序数接尾辞のトークン ("1er"/"2e"/"20ème") も最後に接尾辞を
剥がして裸の数字にする。

## 曖昧クラス (§5.5「ambiguous classes are left untouched」、test_fr.py で列挙)

冠詞と数詞を文脈判定しない=決定論を維持するため、以下は**変換しない**:
  - "un"/"une" 単独 (不定冠詞/数詞の両義)。数詞列の内部 ("vingt et un",
    "quatre-vingt-un") では数詞としてのみ現れるため変換に参加する。
    **cent/mille の余り位置も「数詞列の内部」として一貫適用する**
    ("cent un"=101, "mille et un"=1001。101/1001 の標準形であり、変換しないと
    "101"⇔"cent un" の §5.5 等価が壊れる。検収で確定したバグの修正)。
    両論: 余り位置の "un" が冠詞である並び ("j'en ai cent, un autre…" が
    句読点除去後に "cent un autre" になる等) では誤結合が起こり得るが、
    ref/hyp 双方に同一規則が適用される宣言済みノイズであり、
    vingt-et-un で既に採用済みの「数詞列内部では数詞」の線をこちらだけ
    曲げる方が非一貫 (曖昧クラスの線引きは「単独の un/une」のまま不変)
  - "second"/"seconde(s)" (序数2の異形と名詞「秒」が同形。"deuxième" は
    無曖昧なので変換する)
一方 "neuf" は数詞9と形容詞「新しい」の同形異義だが、口述筆記の文脈では
数詞読みが支配的 (形容詞は後置され頻度も低い) であり、変換しないと
ref/hyp の "9 heures"⇔"neuf heures" 等価が壊れて §5.5 の目的を損なうため、
両論検討の上**変換する**ことを採用した (宣言済みの決定論的選択)。

## §5.6 BasicTextNormalizer とアポストロフィ/小数点の保護

de.py と同じ設計判断 (同ファイル参照): BasicTextNormalizer は記号を一律
スペース化するため、凍結済み §5 ステップ3 の明示例外 (語中アポストロフィ保持)
と本実装の小数点保持を、Private Use Area のプレースホルダで Basic 適用を
またいで保護する。生の Basic ("l'homme"→"l homme") と異なることは宣言済み。

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
# 空白千区切り (NFKC 後なので NBSP/狭域NBSP は通常スペースに揃っているが、
# 念のため両方をパターンに含める)。
_THOUSANDS_SPACE_RE = re.compile(r"(?<=\d)[   ](?=\d{3}(?!\d))")
# 数字トークンの序数接尾辞 (1er, 1re, 2e, 20ème, 20èmes ...)
_DIGIT_ORDINAL_SUFFIX_RE = re.compile(
    r"\b(\d+)(?:ères?|eres?|ers?|res?|èmes?|emes?|e)\b"
)

_basic_normalizer = BasicTextNormalizer()  # remove_diacritics=False (デフォルト)


# --- 綴り数詞の語彙 (casefold 後の表記。無アクセント変種も受理) --------------------

def _with_unaccented_variants(d: dict[str, int]) -> dict[str, int]:
    """é 等を落とした無アクセント表記も同じ値で受理できるよう語彙を複製する。"""
    out = dict(d)
    for word, val in d.items():
        plain = "".join(
            c
            for c in unicodedata.normalize("NFD", word)
            if unicodedata.category(c) != "Mn"
        )
        out.setdefault(plain, val)
    return out


_FR_ZERO = _with_unaccented_variants({"zéro": 0})
_FR_UNITS = {
    "deux": 2, "trois": 3, "quatre": 4, "cinq": 5,
    "six": 6, "sept": 7, "huit": 8, "neuf": 9,
}
_FR_UN = {"un": 1, "une": 1}  # 数詞列の内部でのみ数詞として扱う (曖昧クラス)
_FR_TEENS = {
    "dix": 10, "onze": 11, "douze": 12, "treize": 13,
    "quatorze": 14, "quinze": 15, "seize": 16,
}
# 単純な10の位 (単位/et un を後続できるもの)。soixante と quatre-vingt は
# 10台を後続できるため特別扱い。septante 系はベルギー/スイス変種。
_FR_TENS_SIMPLE = {
    "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
    "septante": 70, "huitante": 80, "octante": 80, "nonante": 90,
}
_FR_PREMIER = _with_unaccented_variants(
    {"premier": 1, "premiers": 1, "première": 1, "premières": 1}
)
# "ième" を剥がした語幹 → 基数語の復元表 (語幹がそのまま基数語のものは不要)。
_FR_ORDINAL_STEM_FIX = {
    "un": "un", "uni": "un",
    "quatr": "quatre", "cinqu": "cinq", "neuv": "neuf",
    "onz": "onze", "douz": "douze", "treiz": "treize",
    "quatorz": "quatorze", "quinz": "quinze", "seiz": "seize",
    "trent": "trente", "quarant": "quarante", "cinquant": "cinquante",
    "soixant": "soixante", "septant": "septante", "huitant": "huitante",
    "octant": "octante", "nonant": "nonante",
    "mill": "mille",
}
_FR_ORDINAL_SUFFIXES = ("ièmes", "ième", "iemes", "ieme")


def _fr_ordinal_value(token: str) -> int | None:
    """単一トークンの序数 (premier / Xième) の値。非序数は None。"""
    if token in _FR_PREMIER:
        return 1
    for suffix in _FR_ORDINAL_SUFFIXES:
        if token.endswith(suffix):
            stem = token[: -len(suffix)]
            word = _FR_ORDINAL_STEM_FIX.get(stem, stem)
            if word == "un":
                return 1
            if word in _FR_UNITS:
                return _FR_UNITS[word]
            if word in _FR_TEENS:
                return _FR_TEENS[word]
            if word in _FR_TENS_SIMPLE:
                return _FR_TENS_SIMPLE[word]
            if word == "soixante":
                return 60
            if word == "cent":
                return 100
            if word == "mille":
                return 1000
            return None
    return None


def _fr_parse_teen(tokens: list[str], i: int) -> tuple[int, int] | None:
    """10-19 (dix-sept 等は2トークン)。(値, 消費トークン数) を返す。"""
    t = tokens[i]
    if t == "dix":
        if i + 1 < len(tokens) and tokens[i + 1] in ("sept", "huit", "neuf"):
            return 10 + _FR_UNITS[tokens[i + 1]], 2
        return 10, 1
    if t in _FR_TEENS:
        return _FR_TEENS[t], 1
    return None


# quatre-vingtième(s): 複合序数 80番目 (ハイフンがステップ3でトークン境界化
# された後の2トークン形。無アクセント変種を含む)。
_FR_QUATRE_VINGT_ORDINALS = ("vingtième", "vingtièmes", "vingtieme", "vingtiemes")


def _fr_parse_0_99(
    tokens: list[str], i: int, in_remainder: bool = False
) -> tuple[int, int] | None:
    """0-99 の数詞列。(値, 消費トークン数) を返す。終端に序数形を許容する。

    in_remainder: cent/mille の余り位置 (=数詞列の内部) を解析中かどうか。
    余り位置では un/une を数詞として受理し ("cent un"=101)、unième 型の
    序数終端も受理する ("deux cent unième"=201)。単独の un/une (冠詞との
    曖昧クラス) はここを通らないため不変換のまま (モジュールdocstring参照)。
    """
    n = len(tokens)
    t = tokens[i]
    if t in _FR_ZERO:
        return 0, 1
    # quatre-vingtième(s) = 80 (複合序数の終端。"quatre"+"vingtième" を
    # 部分変換 "4 20" に割らないための専用規則。モジュールdocstring参照)
    if t == "quatre" and i + 1 < n and tokens[i + 1] in _FR_QUATRE_VINGT_ORDINALS:
        return 80, 2
    # quatre-vingt(s) [+単位/10台]
    if t == "quatre" and i + 1 < n and tokens[i + 1] in ("vingt", "vingts"):
        if i + 2 < n:
            nxt = tokens[i + 2]
            if nxt in _FR_UNITS:
                return 80 + _FR_UNITS[nxt], 3
            if nxt in _FR_UN:
                return 81, 3
            teen = _fr_parse_teen(tokens, i + 2)
            if teen is not None:
                return 80 + teen[0], 2 + teen[1]
            ordinal = _fr_ordinal_value(nxt)
            if ordinal is not None and 1 <= ordinal <= 19:
                return 80 + ordinal, 3
        return 80, 2
    # soixante [+et un/onze | 10台 | 単位]
    if t == "soixante":
        if i + 2 < n and tokens[i + 1] == "et" and tokens[i + 2] in ("un", "une", "onze"):
            return (71 if tokens[i + 2] == "onze" else 61), 3
        if i + 1 < n:
            teen = _fr_parse_teen(tokens, i + 1)
            if teen is not None:
                return 60 + teen[0], 1 + teen[1]
            nxt = tokens[i + 1]
            if nxt in _FR_UNITS:
                return 60 + _FR_UNITS[nxt], 2
            ordinal = _fr_ordinal_value(nxt)
            if ordinal is not None and 1 <= ordinal <= 16:
                return 60 + ordinal, 2
        return 60, 1
    # vingt/trente/... [+et un | 単位]
    if t in _FR_TENS_SIMPLE:
        base = _FR_TENS_SIMPLE[t]
        if i + 2 < n and tokens[i + 1] == "et":
            third = tokens[i + 2]
            if third in _FR_UN:
                return base + 1, 3
            if third in ("unième", "unièmes", "unieme", "uniemes"):
                return base + 1, 3
        if i + 1 < n:
            nxt = tokens[i + 1]
            if nxt in _FR_UNITS:
                return base + _FR_UNITS[nxt], 2
            ordinal = _fr_ordinal_value(nxt)
            if ordinal is not None and 1 <= ordinal <= 9:
                return base + ordinal, 2
        return base, 1
    teen = _fr_parse_teen(tokens, i)
    if teen is not None:
        return teen
    if t in _FR_UNITS:
        return _FR_UNITS[t], 1
    if in_remainder:
        # cent/mille の余り位置は数詞列の内部: un/une は数詞として参加する
        # ("cent un"=101, "mille un"=1001。モジュールdocstring 曖昧クラス参照)。
        if t in _FR_UN:
            return 1, 1
        # unième 型の序数終端 ("deux cent unième"=201)。premier/première は
        # 複合序数の終端に立たないため受理しない (モジュールdocstring参照)。
        if t not in _FR_PREMIER:
            ordinal = _fr_ordinal_value(t)
            if ordinal is not None and 1 <= ordinal <= 99:
                return ordinal, 1
    return None


def _fr_parse_1_999(
    tokens: list[str], i: int, in_remainder: bool = False
) -> tuple[int, int] | None:
    """[係数] cent(s) [+0-99] または 0-99。

    in_remainder は 0-99 へのフォールバック時にそのまま伝播する
    (mille の余り位置から呼ばれた場合)。cent の余りは常に数詞列内部。
    """
    n = len(tokens)
    t = tokens[i]
    if t in _FR_UNITS and i + 1 < n and tokens[i + 1] in ("cent", "cents"):
        value, consumed = _FR_UNITS[t] * 100, 2
    elif t in ("cent", "cents"):
        value, consumed = 100, 1
    else:
        return _fr_parse_0_99(tokens, i, in_remainder)
    if i + consumed < n:
        rest = _fr_parse_0_99(tokens, i + consumed, in_remainder=True)
        if rest is not None:
            return value + rest[0], consumed + rest[1]
    return value, consumed


def _fr_parse_mille_remainder(tokens: list[str], j: int) -> tuple[int, int]:
    """mille の直後の余り。(値, 消費トークン数)、余りが無ければ (0, 0)。

    "et un/une/unième" 型 ("mille et un"=1001, "la mille et unième nuit") と
    通常の 1-999 (数詞列内部として un/une を受理) の両方を受理する。
    """
    n = len(tokens)
    if j + 1 < n and tokens[j] == "et":
        nxt = tokens[j + 1]
        if nxt in _FR_UN or nxt in ("unième", "unièmes", "unieme", "uniemes"):
            return 1, 2
    if j < n:
        rest = _fr_parse_1_999(tokens, j, in_remainder=True)
        if rest is not None:
            return rest
    return 0, 0


def _fr_parse_number_at(tokens: list[str], i: int) -> tuple[int | None, int]:
    """位置 i から始まる最長の数詞列を (値, 消費トークン数) で返す。

    戻り値の規約 (ru.py の _parse_number_run と同型):
      (値, 消費 > 0)    → 変換して消費する。
      (None, 消費 > 0)  → 数詞 run ではあるが範囲超過 (§5.5 の 0-99,999 外)。
                          呼び出し側は run 全体を不変換のまま出力して読み飛ばす
                          (原子的ガード: 部分変換 "100 1000" を生まない)。
      (None, 0)         → 数詞列ではない。
    """
    n = len(tokens)
    sub = _fr_parse_1_999(tokens, i)
    if sub is not None:
        value, consumed = sub
        if i + consumed < n and tokens[i + consumed] == "mille":
            # スケール語は範囲チェックの前に run へ取り込む (先読みで係数だけ
            # 部分確定しない)。範囲超過なら余りまで含めた run 全体を不変換。
            total = value * 1000
            consumed += 1
            rem, rem_consumed = _fr_parse_mille_remainder(tokens, i + consumed)
            total += rem
            consumed += rem_consumed
            if total > 99999:
                return None, consumed
            return total, consumed
        return value, consumed
    if tokens[i] == "mille":
        total, consumed = 1000, 1
        rem, rem_consumed = _fr_parse_mille_remainder(tokens, i + 1)
        return total + rem, consumed + rem_consumed
    ordinal = _fr_ordinal_value(tokens[i])
    if ordinal is not None:
        return ordinal, 1
    return None, 0


def _convert_spelled_numbers(text: str) -> str:
    """§5.5: 綴り数詞列 (基数・序数) を数字に変換する。"""
    tokens = text.split(" ")
    out: list[str] = []
    i = 0
    while i < len(tokens):
        value, consumed = _fr_parse_number_at(tokens, i)
        if consumed == 0:
            out.append(tokens[i])
            i += 1
        elif value is None:
            # 範囲超過 run: 全体を不変換で残す (原子的ガード)。
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

    例外として語中アポストロフィ (§5 ステップ3 明記、l'homme 等) と、数字に
    挟まれた小数点 "." (本実装の決定、モジュールdocstring参照) を保持する。
    """
    text = text.replace("’", "'")
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = _DIGIT_INTERNAL_DOT_RE.sub(_DECIMAL_PLACEHOLDER, text)
    text = "".join(
        " " if unicodedata.category(ch)[0] in ("P", "S") else ch for ch in text
    )
    return text.replace(_APOS_PLACEHOLDER, "'").replace(_DECIMAL_PLACEHOLDER, ".")


def _normalize_steps_1_to_5(text: str) -> str:
    """PREREGISTRATION §5 ステップ1-5 (フランス語向け実装)。"""
    # 1. Unicode NFKC (NBSP/狭域NBSP → 通常スペースを含む)
    text = unicodedata.normalize("NFKC", text)

    # 2. ケースフォールディング
    text = text.casefold()

    # 5 (前倒し実行, モジュールdocstring参照): 小数カンマ→"." → 空白千区切り削除。
    text = text.replace("’", "'")
    text = _DECIMAL_COMMA_RE.sub(".", text)
    text = _THOUSANDS_SPACE_RE.sub("", text)

    # 3. 句読点・記号除去 (P*/S*、語中アポストロフィ・数字間小数点は例外)
    text = _strip_symbols_keep_protected(text)

    # 4. 空白圧縮
    text = _collapse_whitespace(text)

    # 5. 綴り数詞(基数・序数)→数字、数字トークンの序数接尾辞剥がし (1er→1, 2e→2)
    text = _convert_spelled_numbers(text)
    text = _DIGIT_ORDINAL_SUFFIX_RE.sub(r"\1", text)
    text = _collapse_whitespace(text)

    # 空白千区切り融合の再適用 (冪等性のため。モジュールdocstring「千区切り
    # 融合の再適用」参照): 数詞変換が生成した数字の直後に3桁数字が続く形
    # ("dix 300"→"10 300") をここで融合し尽くさないと、出力が2回目の
    # normalize (上の前倒し融合) の不動点にならない。
    text = _THOUSANDS_SPACE_RE.sub("", text)

    return text


def normalize_fr(text: str) -> str:
    """PREREGISTRATION §5 (ステップ1-5 + §5.6 Basic normalizer) を適用する。"""
    text = _normalize_steps_1_to_5(text)

    # §5.6: ピン留めされた Whisper BasicTextNormalizer (remove_diacritics=False)。
    # 語中アポストロフィ・数字間小数点はプレースホルダで保護する。
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = _DIGIT_INTERNAL_DOT_RE.sub(_DECIMAL_PLACEHOLDER, text)
    text = _basic_normalizer(text)
    text = text.replace(_APOS_PLACEHOLDER, "'").replace(_DECIMAL_PLACEHOLDER, ".")

    # 冪等性を保証する最終クリーンアップ (ステップ3の不変条件の再適用 +
    # 空白千区切り融合の不変条件の再適用)。en.py と同じパターン: 出力自体が
    # ステップ3・千区切り融合の双方をパススルーする不動点になることで
    # 冪等性を一般的に保証する。
    text = _strip_symbols_keep_protected(text)
    text = _collapse_whitespace(text)
    text = _THOUSANDS_SPACE_RE.sub("", text)

    return text


def tokenize_fr(text: str) -> list[str]:
    """正規化済みテキストを空白分割する (WER 用)。"""
    normalized = normalize_fr(text)
    if not normalized:
        return []
    return normalized.split(" ")
