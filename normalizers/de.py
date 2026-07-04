"""
ドイツ語テキスト正規化 (PREREGISTRATION §5 の実装)。

パイプライン:
  ステップ1-5 (`_normalize_steps_1_to_5`, 全言語共通の一般規則をドイツ語向けに実装):
    1. Unicode NFKC 正規化
    2. ケースフォールディング (注: casefold は ß→ss を行う。"dreißig" は
       このステップ以降 "dreissig" として扱われるため、数詞語彙も ss 形で持つ)
    3. 句読点・記号除去 (Unicode category P*/S*)。ただし語中アポストロフィは
       保持し、’→' に標準化する (§5 ステップ3 の明記された例外)
    4. 空白の圧縮
    5. 数値等価化: 綴り数詞(基数・序数)→数字、桁区切り除去、
       範囲のハイフンはトークン境界化 (§5.5)
  ステップ6 (§5.6, `normalize_de`):
    ピン留めされた Whisper 公式 BasicTextNormalizer (vendor/whisper_normalizers)
    をステップ1-5の出力の上に適用する。HF Open ASR Leaderboard との比較可能性
    のため。**remove_diacritics はデフォルト (False) を使う**: ダイアクリティクス
    (ü/ö/ä 等) の除去は転写内容の同一性判定を歪める (für と fur は別語) ため
    保持する。HF leaderboard の BasicTextNormalizer 利用もデフォルト設定であり、
    この選択は同 leaderboard との互換性も保つ。
  最終ステップ (冪等性のためのクリーンアップ):
    ステップ3の「P*/S* 除去 (語中アポストロフィ・数字間小数点は例外)」の
    不変条件を最終出力に再適用する (en.py と同じパターン。出力自体が
    ステップ3のパススルー不動点になることで冪等性を一般的に保証する)。

## ステップ順序に関する既知の調整 (§5.5 桁区切りとの整合)

en.py と同じ理由 (同ファイルのモジュールdocstring参照): 桁区切りをステップ3の
一般句読点除去より先に「トークン境界を作らず完全削除」しないと、§5.5 が明記
する等価性 ("33.000" ≡ "33000") を満たせない。よって桁区切り・小数点の処理
だけはステップ3より前に行う。出力の等価性そのものは §5.5 の要求どおり。

## 桁区切り・小数点の扱い (§5.5、ドイツ語の慣習行)

- **千区切り**: ドイツ語は `.` が千区切り。「数字に挟まれた `.` で、直後が
  ちょうど3桁の数字グループ」の場合のみ削除する ("33.000"→"33000"、
  "1.234.567"→"1234567")。「ちょうど3桁」条件により、桁区切りでありえない
  "3.14" のようなパターンを誤って融合しない。スイス式の `'` 千区切り
  ("33'000") も同一規則で削除する (語中アポストロフィ保持の例外より先に処理)。
- **小数点**: ドイツ語は `,` が小数点。数字に挟まれた `,` は `.` に正規化し、
  数字間の `.` はステップ3の除去から保護して1トークンに保つ
  ("3,14"→"3.14")。処理順は「小数カンマ→`.` 変換」の後に「千区切り `.` 削除」
  ("33.000,50"→"33.000.50"→"33000.50" となり正しい)。
- **宣言済みの衝突クラス**: この決定論的規則の下では "1,000" (小数) →"1.000"→
  千区切り規則が発火して "1000" となり、"1.000" (千区切り) と同値になる。
  すなわち「小数部がちょうど3桁の小数」は整数表記と衝突する。ref/hyp 双方に
  同一規則が適用されるため公平であり、§5.5 の範囲ハイフンと同種の
  「宣言済み測定ノイズ」として許容する (文脈で解決しない=決定論の維持)。

## §5.5 綴り数詞→数字 (基数・序数、整数 0–99,999)

ドイツ語の数詞は単一の複合語 ("einundzwanzig"=21, "dreiunddreissigtausend"
=33000) なので、トークン単位の文字列パーサで変換する。合成規則:
  - 1の位+und+10の位 の逆順合成 (einundzwanzig = 1+und+20 = 21)
  - [係数]hundert[余り] (dreihundertfünfundvierzig = 345、hundertundfünf の
    ように余りが und で始まる異表記も受理)。hundert の係数は 1-9 に加えて
    **10-99 (年号型の読み) を許可する**: "achtzehnhundert"=1800、
    "neunzehnhundertvierundachtzig"=1984 (ドイツ語の 1100-1999 の年号は
    tausend でなく hundert 読みが標準形であり、値は §5.5 の宣言範囲
    0-99,999 内。変換しないと "1984"⇔"neunzehnhundertvierundachtzig" の
    数値等価が壊れる。検収で確定した欠落の修正)。係数のない
    "jahrhundert"/"jahrtausend" や "achtziger" 等の非数詞語は左側が数詞に
    パースできないため従来どおり無加工で残る (テストでピン留め)
  - [係数]tausend[余り] (zweitausendsechsundzwanzig = 2026)。結果が 99,999 を
    超えるものは範囲外として変換しない (無加工で残す)。tausend の余りは
    1000 未満に限る (年号型 hundert 許可の副作用で "…tausendachtzehnhundert"
    のような実在しない合成が 1000 以上の余りを作らないためのガード)。
序数は語彙化した語幹 (erst→1, dritt→3, siebt→7 等) と「基数+st」規則
(zwanzigst→20, einundzwanzigst→21) を、格変化語尾 (-e/-en/-er/-es/-em) を
剥がした上で解決し、最終形は §5.5 (en: twentieth→20th→20) と同じく
**裸の数字** とする (der dritte → der 3)。

## 曖昧クラス (§5.5「ambiguous classes are left untouched」、test_de.py で列挙)

冠詞と数詞を文脈判定しない=決定論を維持するため、以下は**変換しない**:
  - "ein" 単独 (不定冠詞/数詞の両義。複合語内 "einundzwanzig"/"einhundert" の
    構成要素としては 1 として扱う。単独の数詞は "eins" であり、こちらは変換する)
  - "eine/einen/einer/einem/eines" (冠詞の格変化形。数詞語彙に含めない)
  - "achte"/"achten" (序数8の変化形と動詞 achten「尊重する」の活用形が同形の
    真の同形異義。ブロックリストで除外し無加工で残す。ja.py の語彙ブロック
    リスト方式と同じ考え方。他の序数変化形 achter/achtes/achtem は動詞形と
    衝突しないため変換する)
一方 "acht" (基数8) は「Acht geben」等の慣用があるが数詞読みが支配的なので
変換する (両論検討の上の採用: 変換しないと ref/hyp の数字⇔綴り不一致が
測定ノイズとして残り、§5.5 の目的である数値等価化が機能しなくなる)。

## §5.6 BasicTextNormalizer とアポストロフィ/小数点の保護

BasicTextNormalizer は記号を一律スペース化するため、素通しすると §5 ステップ3
が明示的に保持を定める語中アポストロフィと、上記で決定した数字間小数点が
破壊される。両論: (A) HF leaderboard の生の Basic 挙動に完全一致させる
(アポストロフィもスペース化)、(B) 凍結済み §5 ステップ3 の明示例外を最終出力
まで維持する。凍結仕様の明文 (「word-internal apostrophes ... are kept」) が
優先されるため (B) を採用し、Private Use Area のプレースホルダで Basic 適用を
またいで保護する。この点が生の Basic と異なることは宣言済みの設計判断である。

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

# 語中アポストロフィ/数字間小数点を一時退避するプレースホルダ。
# Private Use Area の文字 (Unicode category "Co") を使う: 通常の入力には
# 現れず、P*/S* 除去にも BasicTextNormalizer の記号除去にも影響されない。
_APOS_PLACEHOLDER = ""
_DECIMAL_PLACEHOLDER = ""

_WHITESPACE_RE = re.compile(r"\s+")
_WORD_INTERNAL_APOS_RE = re.compile(r"(?<=\w)'(?=\w)")
_DIGIT_INTERNAL_DOT_RE = re.compile(r"(?<=\d)\.(?=\d)")
# 小数点: 数字に挟まれたカンマ → "." (ドイツ語の小数慣習)
_DECIMAL_COMMA_RE = re.compile(r"(?<=\d),(?=\d)")
# 千区切り: 数字に挟まれた "." / スイス式 "'" で直後がちょうど3桁のもの
_THOUSANDS_DOT_RE = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")
_THOUSANDS_APOS_RE = re.compile(r"(?<=\d)'(?=\d{3}(?!\d))")

# §5.6: remove_diacritics=False (デフォルト)。理由はモジュールdocstring参照。
_basic_normalizer = BasicTextNormalizer()


# --- 綴り数詞の語彙 (casefold 後の表記。ß→ss 済み) -------------------------------

_DE_UNITS = {
    "null": 0, "eins": 1, "zwei": 2, "drei": 3, "vier": 4,
    "fünf": 5, "sechs": 6, "sieben": 7, "acht": 8, "neun": 9,
}
# 複合語の構成要素としてのみ 1 と読む "ein" (単独では曖昧クラス)。
_DE_UNITS_COMPOUND = dict(_DE_UNITS, ein=1)
_DE_TEENS = {
    "zehn": 10, "elf": 11, "zwölf": 12, "dreizehn": 13, "vierzehn": 14,
    "fünfzehn": 15, "sechzehn": 16, "siebzehn": 17, "achtzehn": 18,
    "neunzehn": 19,
}
_DE_TENS = {
    "zwanzig": 20, "dreissig": 30, "vierzig": 40, "fünfzig": 50,
    "sechzig": 60, "siebzig": 70, "achtzig": 80, "neunzig": 90,
}
# 序数の語彙化した語幹 (1-19)。20以上は「基数+st」規則で解決する。
_DE_ORDINAL_STEMS = {
    "erst": 1, "zweit": 2, "dritt": 3, "viert": 4, "fünft": 5,
    "sechst": 6, "siebt": 7, "siebent": 7, "acht": 8, "neunt": 9,
    "zehnt": 10, "elft": 11, "zwölft": 12, "dreizehnt": 13, "vierzehnt": 14,
    "fünfzehnt": 15, "sechzehnt": 16, "siebzehnt": 17, "achtzehnt": 18,
    "neunzehnt": 19,
}
_DE_ORDINAL_INFLECTIONS = ("en", "er", "es", "em", "e")  # 長い語尾から試す

# 曖昧クラスのブロックリスト (モジュールdocstring参照)。
_DE_AMBIGUOUS_BLOCKLIST = {"ein", "achte", "achten"}


def _de_parse_0_99(s: str) -> int | None:
    """0-99 の複合語部分をパースする (複合語文脈なので ein=1 を許容)。"""
    if s == "":
        return None
    if s in _DE_UNITS_COMPOUND:
        return _DE_UNITS_COMPOUND[s]
    if s in _DE_TEENS:
        return _DE_TEENS[s]
    if s in _DE_TENS:
        return _DE_TENS[s]
    # 逆順合成: <unit>und<tens> (einundzwanzig = 21)
    for tens_word, tens_val in _DE_TENS.items():
        if s.endswith(tens_word):
            head = s[: -len(tens_word)]
            if head.endswith("und"):
                unit = head[:-3]
                if unit in _DE_UNITS_COMPOUND:
                    return _DE_UNITS_COMPOUND[unit] + tens_val
    return None


def _de_parse_0_9999(s: str) -> int | None:
    """hundert 複合語 (または 0-99)。

    hundert の係数は 1-9 に加えて 10-99 (年号型: "achtzehnhundert"=1800、
    "neunzehnhundertvierundachtzig"=1984) を許可するため、最大値は 9999
    (モジュールdocstring §5.5 参照。旧名 _de_parse_0_999)。係数 0
    ("nullhundert") は実在しない形なので数詞と認めない。
    """
    if s == "":
        return None
    if "hundert" in s:
        left, _, right = s.partition("hundert")
        left_val = 1 if left == "" else _de_parse_0_99(left)
        if left_val is None or left_val == 0:
            return None
        if right.startswith("und"):  # hundertundfünf 異表記
            right = right[3:]
        right_val = 0 if right == "" else _de_parse_0_99(right)
        if right_val is None:
            return None
        return left_val * 100 + right_val
    return _de_parse_0_99(s)


def _de_parse_cardinal(s: str) -> int | None:
    """基数複合語を 0-99,999 の整数へ変換する。範囲外・非数詞は None。"""
    if "tausend" in s:
        left, _, right = s.partition("tausend")
        left_val = 1 if left == "" else _de_parse_0_9999(left)
        if left_val is None:
            return None
        if right.startswith("und"):
            right = right[3:]
        right_val = 0 if right == "" else _de_parse_0_9999(right)
        if right_val is None or right_val >= 1000:
            # tausend の余りは 1000 未満のみ (モジュールdocstring参照)。
            return None
        val = left_val * 1000 + right_val
        return val if val <= 99999 else None
    return _de_parse_0_9999(s)


def _de_ordinal_stem_value(stem: str) -> int | None:
    if stem in _DE_ORDINAL_STEMS:
        return _DE_ORDINAL_STEMS[stem]
    # 基数+st 規則 (zwanzigst→20, einundzwanzigst→21, hundertst→100)
    if stem.endswith("st"):
        base = _de_parse_cardinal(stem[:-2])
        if base is not None:
            return base
    # 複合序数: <基数 (hundert/tausend で終わる)> + <小序数語幹>
    # (hundertdritt → 103)
    for small, small_val in _DE_ORDINAL_STEMS.items():
        if stem.endswith(small) and len(stem) > len(small):
            prefix = stem[: -len(small)]
            if prefix.endswith(("hundert", "tausend")):
                prefix_val = _de_parse_cardinal(prefix)
                if prefix_val is not None:
                    return prefix_val + small_val
    return None


def _de_parse_ordinal(token: str) -> int | None:
    """序数 (格変化語尾つき) を裸の数字へ。非序数は None。"""
    for suffix in _DE_ORDINAL_INFLECTIONS:
        if token.endswith(suffix):
            val = _de_ordinal_stem_value(token[: -len(suffix)])
            if val is not None:
                return val
    return None


def _convert_spelled_numbers(text: str) -> str:
    """§5.5: 綴り数詞 (基数・序数) トークンを数字に変換する。"""
    out = []
    for token in text.split(" "):
        if token in _DE_AMBIGUOUS_BLOCKLIST:
            out.append(token)
            continue
        val = _de_parse_cardinal(token)
        if val is None:
            val = _de_parse_ordinal(token)
        out.append(str(val) if val is not None else token)
    return " ".join(out)


def _collapse_whitespace(text: str) -> str:
    return _WHITESPACE_RE.sub(" ", text).strip()


def _strip_symbols_keep_protected(text: str) -> str:
    """§5 ステップ3の句読点・記号除去 (P*/S*)。

    例外として語中アポストロフィ (§5 ステップ3 明記) と、数字に挟まれた
    小数点 "." (§5.5 の本実装の決定、モジュールdocstring参照) を保持する。
    ステップ1-5の内部でも、§5.6 のあとの最終クリーンアップでも共有して使う。
    """
    text = text.replace("’", "'")
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = _DIGIT_INTERNAL_DOT_RE.sub(_DECIMAL_PLACEHOLDER, text)
    text = "".join(
        " " if unicodedata.category(ch)[0] in ("P", "S") else ch for ch in text
    )
    return text.replace(_APOS_PLACEHOLDER, "'").replace(_DECIMAL_PLACEHOLDER, ".")


def _normalize_steps_1_to_5(text: str) -> str:
    """PREREGISTRATION §5 ステップ1-5 (ドイツ語向け実装)。"""
    # 1. Unicode NFKC
    text = unicodedata.normalize("NFKC", text)

    # 2. ケースフォールディング (ß→ss を含む)
    text = text.casefold()

    # 5 (前倒し実行, モジュールdocstring参照): 桁区切り・小数点。
    # 順序: スイス式 ' 千区切り削除 → 小数カンマ→"." → "." 千区切り削除。
    text = text.replace("’", "'")
    text = _THOUSANDS_APOS_RE.sub("", text)
    text = _DECIMAL_COMMA_RE.sub(".", text)
    text = _THOUSANDS_DOT_RE.sub("", text)

    # 3. 句読点・記号除去 (P*/S*、語中アポストロフィ・数字間小数点は例外)
    text = _strip_symbols_keep_protected(text)

    # 4. 空白圧縮
    text = _collapse_whitespace(text)

    # 5. 綴り数詞(基数・序数)→数字
    text = _convert_spelled_numbers(text)
    text = _collapse_whitespace(text)

    return text


def normalize_de(text: str) -> str:
    """PREREGISTRATION §5 (ステップ1-5 + §5.6 Basic normalizer) を適用する。"""
    text = _normalize_steps_1_to_5(text)

    # §5.6: ピン留めされた Whisper BasicTextNormalizer (remove_diacritics=False)
    # をステップ1-5の上に適用。語中アポストロフィと数字間小数点は §5 ステップ3
    # の例外を維持するためプレースホルダで保護する (モジュールdocstring参照)。
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = _DIGIT_INTERNAL_DOT_RE.sub(_DECIMAL_PLACEHOLDER, text)
    text = _basic_normalizer(text)
    text = text.replace(_APOS_PLACEHOLDER, "'").replace(_DECIMAL_PLACEHOLDER, ".")

    # 冪等性を保証する最終クリーンアップ (ステップ3の不変条件の再適用。
    # en.py と同じパターン: 出力が常にステップ3のパススルー不動点になる)。
    text = _strip_symbols_keep_protected(text)
    text = _collapse_whitespace(text)

    return text


def tokenize_de(text: str) -> list[str]:
    """正規化済みテキストを空白分割する (WER 用)。"""
    normalized = normalize_de(text)
    if not normalized:
        return []
    return normalized.split(" ")
