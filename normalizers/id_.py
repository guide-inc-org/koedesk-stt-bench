"""インドネシア語テキスト正規化 — PREREGISTRATION.md §5 (Normalization) のインドネシア語部分を実装する。

モジュール名について: 言語コードどおりの `id.py` にすると、モジュール名 `id` が
Python の組み込み関数 `id()` と衝突し (シャドーイングによる可読性低下・linter
警告)、`from normalizers import id` のような import 文も紛らわしくなるため、
PEP 8 の「予約語・組み込み名と衝突する識別子には末尾アンダースコアを付ける」
慣行に倣い `id_.py` とする。公開関数名は他言語と同型の
`normalize_id` / `tokenize_id` (こちらは属性名なので衝突しない)。

対応する仕様セクション:
    §5 手順1-4 (共通パイプライン: NFKC / ケースフォールド /
                記号除去(語中アポストロフィ例外あり=ラテン文字言語) / 空白畳み込み)
    §5.5       (数値等価性: 綴り数詞→数字、桁区切り除去)
    §5.6 (id)  (「ko / vi / id / ru: steps 1–5 plus whitespace-delimited WER」
                = 追加の言語固有規則なし。WERトークナイザは空白分割)

--------------------------------------------------------------------------
【実装上の解釈が必要だった箇所 — 仕様の例を満たすための唯一解 (en.py/ja.py と同一論点)】

桁区切り除去 (§5.5) と記号除去 (§5 手順3) の順序:
    桁区切り記号 (P*) を先に一般記号除去するとトークン境界 (空白) 化してしまい、
    §5.5 の「桁区切りは数トークン内部から除去」を満たせない。よって
    「数字に挟まれた桁区切りの完全削除」を一般記号除去より前に実行する。

--------------------------------------------------------------------------
【§5.5 桁区切りの言語別慣習 (id の行)】

インドネシア語の慣習は vi と同じ「.」= 千区切り、「,」= 小数点
(33.000 = 33000、3,5 = 3.5)。vi.py と同じ判断 (同 docstring の両論併記を参照) で、
ピリオドは「直後がちょうど3桁の数字列」の場合のみ桁区切りとして削除する
(案B: 正当な桁区切りを取りこぼさず、英語式小数 "3.5" を 35 に壊さない)。
小数点のカンマ ("3,5") は §5.5 の対象範囲 (整数) 外なので特別扱いせず、
手順3の一般記号除去でトークン境界になる ("3 5") — レンジのハイフン
(25-30→25 30) と同じ「宣言済みノイズ」クラス。

--------------------------------------------------------------------------
【§5.5 綴り数詞→数字 変換の保守的ルール】

対象範囲: 0〜99,999 の整数 (仕様どおり)。決定論・文脈判定なし。

数詞語彙:
    基数   satu(1) dua(2) tiga(3) empat(4) lima(5) enam(6) tujuh(7)
           delapan(8) sembilan(9)
    乗数   puluh(×10) belas(+10: 12〜19) ratus(×100) ribu(×1000)
    se-合成形 (語彙化した完全一致4形のみ):
           sepuluh(10) sebelas(11) seratus(100) seribu(1000)

変換条件 (すべて満たす run のみ変換):
  1. 数詞語彙トークンの最大連続列 (run) が乗数系トークン
     {puluh, belas, ratus, ribu, sepuluh, sebelas, seratus, seribu} を
     少なくとも1つ含む。
     → **単独の基数語は不変換** (保守線; vi と同じ)。salah satu (〜のひとつ)・
       satu-satunya (唯一の)・数え上げ列 (satu dua tiga) などの慣用を守る。
  2. run 全体が下記の厳密文法で完全にパースでき、値が 0〜99,999 に収まる。
     部分列の貪欲変換はしない (パース失敗時は run 全体を不変換)。

厳密文法 (標準インドネシア語数表現のみ):
  - 十位: [d puluh] = d×10、[d puluh u] = d×10+u、[d belas] = 10+d
    (d, u ∈ satu…sembilan ただし十位係数・belas 係数は dua…sembilan)。
    [sepuluh] = 10、[sebelas] = 11。
    **非標準形 satu puluh / satu belas は不変換** (標準形は sepuluh / sebelas
    のみ。非標準形を認めるのは規則の追加になるため、最小の標準文法に留める)。
  - 百/千位: ratus/ribu の直前に係数が必須 (裸の ratus/ribu は不変換:
    ratusan/ribuan のような派生語はそもそも語彙外)。se- 合成形 seratus/seribu
    は係数1として機能し、直前に係数を置けない (dua seribu は不変換)。
  - **乗数語の後の裸の単位桁1語は変換する** (seratus lima = 105、
    dua ribu lima = 2005)。vi と線引きが異なる点なので理由を明記する:
    標準インドネシア語の正書法・文法では「乗数+単位桁」がそのまま
    一の位を表す標準形であり (105 の標準の読みは seratus lima)、vi の
    linh/lẻ に相当する必須の連結詞が存在しない。また vi で禁止の決め手だった
    同綴り異義 (năm=年) にあたる語も id の基数にはない (lima 等は数詞専用)。
    口語の省略読み (市場口語で dua ribu lima を 2500 と読む用法) は
    ref/hyp 対称の宣言済みノイズとして許容する。

序数の扱い (不変換 = 曖昧クラス):
  - pertama (第1・補充形)、ke-N / kedua / ketiga … は**変換しない**。
    決定的理由: kedua は「第2の」と「両方の」(kedua orang itu = その2人とも) の
    完全同形で、文脈判定なしには区別できない。pertama は数詞形態素を含まない
    補充形。kesatu/kedua 等の接頭辞合成語は1語であり数詞語彙に含めないため、
    構造的に不変換となる。"ke-2" はハイフンが手順3でトークン境界化して
    "ke 2" になる (宣言済みノイズ)。en (twentieth→20) と扱いが異なるのは
    言語事実による線引きで、ref/hyp 対称なので公平性は保たれる。

ゼロの扱い:
  - nol / kosong (0) は数詞語彙に**含めない** (不変換)。標準の数合成に
    ゼロ音節は現れず (2026 = dua ribu dua puluh enam、vi の không trăm 相当の
    必須要素がない)、kosong は「空の」の同綴り異義が支配的なため。
    小数 (nol koma lima = 0,5) は §5.5 の対象範囲外。

既知の残存限界 (意図的に許容し宣言する):
  - ASCII 数字と綴り数詞の混在 ("20 ribu") は結合しない (ribu 単独 run は
    係数なしでパース失敗=不変換)。
  - seribu satu (千夜一夜的な慣用「非常に多くの」) は文字どおり 1001 に
    変換される。数値読みも正当なため一律ブロックはせず、実データで問題化
    したらブロックリスト追記+テスト列挙の運用とする (ja.py と同じ方針)。
"""

from __future__ import annotations

import re
import unicodedata

# 語中アポストロフィを一時退避するプレースホルダ (en.py と同じ手法・同じ文字。
# Private Use Area の文字 = Unicode category "Co" のため P*/S* 除去の対象外)。
_APOS_PLACEHOLDER = ""

_WHITESPACE_RE = re.compile(r"\s+")
# 桁区切りピリオド: 直後がちょうど3桁のときのみ (モジュールdocstring 参照)。
_DIGIT_GROUP_SEP_RE = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")
_WORD_INTERNAL_APOS_RE = re.compile(r"(?<=\w)'(?=\w)")


# --- 数詞語彙 (§5.5) --------------------------------------------------------------

_DIGITS = {
    "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5,
    "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9,
}

# 十位係数・belas 係数 (dua belas=12 … sembilan belas=19)。satu は除外
# (標準形は sepuluh / sebelas)。
_TENS_COEFF = {k: v for k, v in _DIGITS.items() if k != "satu"}

_SEPULUH = "sepuluh"   # 10
_SEBELAS = "sebelas"   # 11
_PULUH = "puluh"       # ×10
_BELAS = "belas"       # +10

# スケール語 (降順)。(通常形, se-合成形, 乗数)
_SCALES: list[tuple[str, str, int]] = [
    ("ribu", "seribu", 1_000),
    ("ratus", "seratus", 100),
]

_MULTIPLIERS = frozenset(
    {_SEPULUH, _SEBELAS, _PULUH, _BELAS}
    | {w for word, se_form, _ in _SCALES for w in (word, se_form)}
)

# run 検出用の数詞語彙全体。
_NUMBER_WORDS = frozenset(set(_DIGITS) | _MULTIPLIERS)

_MAX_VALUE = 99_999


# --- 厳密パーサ (§5.5) ------------------------------------------------------------


def _parse_tens(tokens: list[str]) -> int | None:
    """十位以下 (0〜99) の厳密パース。パターン外は None (=run 全体が不変換)。"""
    if not tokens:
        return 0
    if len(tokens) == 1:
        if tokens[0] == _SEPULUH:
            return 10
        if tokens[0] == _SEBELAS:
            return 11
        if tokens[0] in _DIGITS:
            # 裸の単位桁。到達するのは係数位置かスケール語の残余のみ
            # (単独 run は乗数語必須の変換条件1で除外済み)。
            return _DIGITS[tokens[0]]
        return None
    if len(tokens) == 2:
        if tokens[1] == _BELAS and tokens[0] in _TENS_COEFF:
            return 10 + _TENS_COEFF[tokens[0]]
        if tokens[1] == _PULUH and tokens[0] in _TENS_COEFF:
            return _TENS_COEFF[tokens[0]] * 10
        return None
    if len(tokens) == 3:
        if (
            tokens[1] == _PULUH
            and tokens[0] in _TENS_COEFF
            and tokens[2] in _DIGITS
        ):
            return _TENS_COEFF[tokens[0]] * 10 + _DIGITS[tokens[2]]
        return None
    return None


def _parse_scaled(tokens: list[str], scale_idx: int) -> int | None:
    """スケール語 (ribu/seribu → ratus/seratus) を降順に処理する再帰パーサ。"""
    if scale_idx == len(_SCALES):
        return _parse_tens(tokens)

    word, se_form, mult = _SCALES[scale_idx]
    pos = next((i for i, t in enumerate(tokens) if t in (word, se_form)), None)
    if pos is None:
        return _parse_scaled(tokens, scale_idx + 1)

    left, right = tokens[:pos], tokens[pos + 1:]

    # 係数。se-合成形は「係数1が語彙化した形」なので直前に係数を置けない。
    if tokens[pos] == se_form:
        if left:
            return None  # dua seribu のような非標準形は不変換
        coeff = 1
    else:
        if not left:
            return None  # 裸の ratus/ribu は不変換
        coeff = _parse_scaled(left, scale_idx + 1)
        if coeff is None or coeff == 0:
            return None

    rem = _parse_scaled(right, scale_idx + 1) if right else 0
    if rem is None or rem >= mult:
        return None
    return coeff * mult + rem


def _parse_number_run(tokens: list[str]) -> int | None:
    return _parse_scaled(tokens, 0)


def _convert_number_word_runs(text: str) -> str:
    """空白区切りトークン列の中の数詞 run を検出し、変換可能なら数字へ置換する。"""
    if not text:
        return text
    tokens = text.split(" ")
    out: list[str] = []
    i = 0
    while i < len(tokens):
        if tokens[i] not in _NUMBER_WORDS:
            out.append(tokens[i])
            i += 1
            continue
        j = i
        while j < len(tokens) and tokens[j] in _NUMBER_WORDS:
            j += 1
        run = tokens[i:j]
        value = None
        if any(t in _MULTIPLIERS for t in run):  # 変換条件1 (乗数語必須)
            value = _parse_number_run(run)
        if value is not None and 0 <= value <= _MAX_VALUE:
            out.append(str(value))
        else:
            out.extend(run)  # 全か無か: パース失敗は run 全体を不変換
        i = j
    return " ".join(out)


# --- 記号除去 (語中アポストロフィ例外つき、en.py と同じ手法) -----------------------


def _strip_symbols_keep_apostrophe(text: str) -> str:
    """§5 手順3の句読点・記号除去 (P*/S*、語中アポストロフィは例外)。

    id はラテン文字言語なので §5 手順3の例外 (word-internal apostrophes kept、
    ’→' 標準化) が適用される (Jum'at のような綴りが実在する)。
    """
    text = text.replace("’", "'")
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = "".join(
        " " if unicodedata.category(ch)[0] in ("P", "S") else ch for ch in text
    )
    return text.replace(_APOS_PLACEHOLDER, "'")


# --- メインパイプライン -----------------------------------------------------------


def normalize_id(text: str) -> str:
    """PREREGISTRATION.md §5 のインドネシア語正規化パイプライン (手順1-5)。"""
    # 1. Unicode NFKC
    text = unicodedata.normalize("NFKC", text)

    # 2. ケースフォールディング
    text = text.casefold()

    # 3. 桁区切り除去 (§5.5 id の行: "." 千区切り、3桁グループ条件つき) —
    #    一般記号除去より前に実行する理由はモジュールdocstringを参照。
    text = _DIGIT_GROUP_SEP_RE.sub("", text)

    # 4. 記号・句読点の除去 (§5 手順3、P*/S*。語中アポストロフィは例外保持)
    text = _strip_symbols_keep_apostrophe(text)

    # 5. 空白畳み込み (§5 手順4)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    # 6. 綴り数詞→数字 (§5.5)
    text = _convert_number_word_runs(text)

    return text


def tokenize_id(text: str) -> list[str]:
    """WER計算用トークナイザ。§5.6 (id) の指定どおり空白分割。

    en.py の tokenize_en と同じ流儀で、内部で normalize_id() を適用してから
    分割する (生テキストを渡してよい)。
    """
    normalized = normalize_id(text)
    if not normalized:
        return []
    return normalized.split(" ")
