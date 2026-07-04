"""ベトナム語テキスト正規化 — PREREGISTRATION.md §5 (Normalization) のベトナム語部分を実装する。

対応する仕様セクション:
    §5 手順1-4 (共通パイプライン: NFKC / ケースフォールド /
                記号除去(語中アポストロフィ例外あり=ラテン文字言語) / 空白畳み込み)
    §5.5       (数値等価性: 綴り数詞→数字、桁区切り除去)
    §5.6 (vi)  (「ko / vi / id / ru: steps 1–5 plus whitespace-delimited WER」
                = 追加の言語固有規則なし。WERトークナイザは空白分割)

NFKC について: エンジン出力の声調付き文字は合成済み (NFC) と分解済み (NFD) の
両形で届きうるが、手順1の NFKC が正準合成を行うため、本モジュールの数詞語彙
(合成済み形で保持) と常に一致する。語彙テーブルはモジュール読み込み時に
NFKC+casefold を通して構築し、ソースファイルの符号化形に依存しないようにする。

--------------------------------------------------------------------------
【実装上の解釈が必要だった箇所 — 仕様の例を満たすための唯一解 (en.py/ja.py と同一論点)】

桁区切り除去 (§5.5) と記号除去 (§5 手順3) の順序:
    桁区切り記号 (P*) を先に一般記号除去するとトークン境界 (空白) 化してしまい、
    §5.5 の「桁区切りは数トークン内部から除去」を満たせない。よって
    「数字に挟まれた桁区切りの完全削除」を一般記号除去より前に実行する。

--------------------------------------------------------------------------
【§5.5 桁区切りの言語別慣習 (vi の行) — 両論併記】

ベトナム語の慣習は「.」= 千区切り、「,」= 小数点 (33.000 = 33000、3,5 = 3.5)。

  案A (en.py のカンマ規則の単純移植): (?<=\\d)\\.(?=\\d) で数字間のピリオドを
      すべて削除する。
  案B (採用): ピリオドの直後が「ちょうど3桁の数字列」の場合のみ桁区切りと
      みなして削除する ((?<=\\d)\\.(?=\\d{3}(?!\\d)))。

  案Bを採用した理由: 千区切りは必ず3桁グループを作るので、この条件は正当な
  桁区切り (33.000 / 1.234.567) を全く取りこぼさない。一方、案Aはエンジンが
  英語式の小数点を出力した場合 ("3.5") に 35 という**別の数値**へ壊してしまう。
  案Bなら "3.5" はピリオドが手順3の一般記号除去でトークン境界になり "3 5" と
  なる — 数値としては壊れるが、これは §5.5 がレンジのハイフン (25-30→25 30) に
  ついて宣言しているのと同じ「トークン境界化による宣言済みノイズ」クラスで
  あり、誤った数値の合成よりも影響が小さい。

  小数点のカンマ ("3,5") は §5.5 の対象範囲 (整数 0–99,999) 外なので特別扱い
  せず、手順3の一般記号除去でトークン境界になる ("3 5")。同じく宣言済みノイズ。

--------------------------------------------------------------------------
【§5.5 綴り数詞→数字 変換の保守的ルール】

対象範囲: 0〜99,999 の整数 (仕様どおり)。決定論・文脈判定なし。

数詞語彙:
    基数     một(1) hai(2) ba(3) bốn(4) năm(5) sáu(6) bảy(7) tám(8) chín(9) không(0)
    位置異形 mốt(1: mươi直後) tư(4: 十位の後) lăm(5: mười/mươi直後)
    乗数     mười(10) mươi(×10) trăm(100) nghìn/ngàn(1000) vạn(10000)
    連結詞   linh / lẻ (百位の後の「飛び」: một trăm linh năm = 105)

変換条件 (すべて満たす run のみ変換):
  1. 数詞語彙トークンの最大連続列 (run) が乗数語
     {mười, mươi, trăm, nghìn, ngàn, vạn} を少なくとも1つ含む。
     → **単独の基数語は不変換** (曖昧クラス)。理由: một は冠詞的用法
       (một chút = 少し)、năm は「年」、ba は「父」、chín は「熟した」、
       tư は「私的/第4」、không は否定辞「〜ない」と、単独では非数詞の
       同綴り異義が支配的なため。数え上げ列 (một hai ba) も同様に不変換。
  2. run 全体が下記の厳密文法で完全にパースでき、値が 0〜99,999 に収まる。
     部分列の貪欲変換はしない (どこで切るかの恣意性を生むため、
     パース失敗時は run 全体を不変換とする全か無かの規則)。
     **唯一の決定論的バックオフ (検収で確定した欠落の修正)**: run 全体の
     パースが失敗し、かつ run の先頭が下記に列挙する「先頭曖昧係数語」の
     場合に限り、その1語を run から外して残りを再パースする。成功すれば
     「外した語 + 変換後の数字」を出力する。対象は
       - năm (名詞「年」): "năm hai nghìn không trăm hai mươi sáu"
         (= năm 2026 の読み下し) → "năm 2026"。năm が「年」である読みが
         run 先頭では支配的で、かつ後続が完全な数詞列を成すため。
     の1語のみ (một/ba/tư/chín 等の他の同綴り異義語は、先頭に立って直後に
     完全な数詞列が続く高頻度パターンが実在しないため列挙しない)。
     バックオフは「先頭の1語を1回だけ外す」以外の探索をしない (どこで
     切るかの恣意性を再導入しないための線引き)。両論: バックオフ自体を
     置かない案 (全か無かの純粋形) は年号の読み下しという高頻度クラスを
     丸ごと不変換にし、"năm 2026"⇔読み下しの §5.5 等価を失うため不採用。
     既存の宣言済み挙動 (hai mươi năm / mười năm / hai nghìn năm の不変換)
     は run 先頭が năm でないため影響を受けない (テストでピン留め)。

厳密文法 (標準ベトナム語数表現のみ; 決定論のための線引きを含む):
  - 十位: [d mươi] = d×10 (d ∈ hai…chín; năm は係数として許す: năm mươi=50)、
    [d mươi u] = d×10+u、[mười]=10、[mười u]=10+u。
  - **mươi 直後の単位桁は mốt/hai/ba/bốn/tư/lăm/sáu/bảy/tám/chín のみ**。
    một と năm は認めない。理由: 標準形は mốt/lăm であり、năm を認めると
    「hai mươi năm = 20年」を 25 に誤変換する (năm=年 の同綴り異義)。
    một は mười 直後のみ許可 (mười một = 11 が標準形)。
    **mười 直後の năm も認めない** (mười năm = 10年; 15 は mười lăm のみ)。
  - 百/千/万位: 乗数語の直前に係数が必須 (裸の trăm/nghìn/vạn は不変換:
    hàng nghìn = 「何千もの」等の非数値用法を守る)。không は trăm の係数
    としてのみ 0 を許す (hai nghìn không trăm hai mươi sáu = 2026)。
  - 連結詞 linh/lẻ の直後は単位桁1語のみ (một trăm linh năm = 105、
    hai nghìn lẻ năm = 2005)。linh/lẻ の後の năm は 5 と認める
    (連結詞は数値文脈を一意に確定させるため同綴り異義が生じない)。
  - **乗数語の直後に linh/lẻ なしで裸の単位桁1語が続く形は不変換**
    (パース失敗)。理由: 「hai nghìn năm」は 2005 ではなく「2000年」の可能性が
    高く、「hai trăm ba」は口語の省略 (=230) と 203 の両義があるため。
    105 は một trăm linh năm / một trăm lẻ năm の標準形のみ変換する。
  - vạn (万) は古風だが §5.5 の範囲内なので係数付きのみ対応 (một vạn = 10000)。

序数の扱い (不変換 = 曖昧クラス):
  - thứ N (thứ nhất, thứ hai, …) は**変換しない**。決定的理由: thứ hai(月曜)〜
    thứ bảy(土曜) は曜日名と完全同形であり、文脈判定なしには序数と区別
    できない。en (twentieth→20) と扱いが異なるのは言語事実による線引きで、
    ref/hyp 対称なので公平性は保たれる。thứ nhất の nhất はそもそも数詞語彙に
    含めない (nhất 単独は「最も」)。thứ は数詞語彙外なので、後続の単独基数語は
    条件1で自然に不変換となる (thứ hai → thứ hai のまま)。

既知の残存限界 (意図的に許容し宣言する):
  - không は否定辞として高頻度なため、数詞 run に隣接すると run に取り込まれ、
    パース失敗で run 全体が不変換になることがある (có ba mươi không? の
    ba mươi は変換されない)。年号読み (hai nghìn không trăm…) の変換を守る
    ための取り込みであり、ref/hyp 対称の宣言済みノイズ。
  - ASCII 数字と綴り数詞の混在 ("20 nghìn") は結合しない (nghìn 単独 run は
    係数なしでパース失敗=不変換)。
"""

from __future__ import annotations

import re
import unicodedata

# 語中アポストロフィを一時退避するプレースホルダ (en.py と同じ手法。
# Private Use Area の文字 = Unicode category "Co" のため P*/S* 除去の対象外)。
_APOS_PLACEHOLDER = ""

_WHITESPACE_RE = re.compile(r"\s+")
# 桁区切りピリオド: 直後がちょうど3桁のときのみ (モジュールdocstring 案B)。
_DIGIT_GROUP_SEP_RE = re.compile(r"(?<=\d)\.(?=\d{3}(?!\d))")
_WORD_INTERNAL_APOS_RE = re.compile(r"(?<=\w)'(?=\w)")


def _n(word: str) -> str:
    """語彙テーブル構築用: パイプライン手順1-2と同じ NFKC+casefold を適用する。"""
    return unicodedata.normalize("NFKC", word).casefold()


# --- 数詞語彙 (§5.5) --------------------------------------------------------------

# 係数 (乗数語の直前に立てる基数)。tư/mốt/lăm は位置異形なので係数にならない。
_COEFF = {_n(k): v for k, v in {
    "một": 1, "hai": 2, "ba": 3, "bốn": 4, "năm": 5,
    "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}.items()}

# 十位の係数 (d mươi)。một mươi は標準形でないため除外 (10 は mười)。
_TENS_COEFF = {_n(k): v for k, v in {
    "hai": 2, "ba": 3, "bốn": 4, "năm": 5,
    "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}.items()}

# mươi 直後の単位桁。một(→mốt)/năm(→lăm) は不許可 (docstring 参照)。
_UNIT_AFTER_MUOI = {_n(k): v for k, v in {
    "mốt": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4,
    "lăm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}.items()}

# mười (10) 直後の単位桁 (11〜19)。một は許可 (mười một=11)、năm は不許可
# (mười năm=10年; 15 は mười lăm)。
_UNIT_AFTER_MUOI10 = {_n(k): v for k, v in {
    "một": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4,
    "lăm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}.items()}

# linh/lẻ 直後の単位桁。連結詞が数値文脈を確定させるため năm も 5 と認める。
_UNIT_AFTER_LINH = {_n(k): v for k, v in {
    "một": 1, "hai": 2, "ba": 3, "bốn": 4, "tư": 4,
    "năm": 5, "lăm": 5, "sáu": 6, "bảy": 7, "tám": 8, "chín": 9,
}.items()}

_MUOI10 = _n("mười")   # 10
_MUOI = _n("mươi")     # ×10
_ZERO = _n("không")    # 0 (trăm の係数としてのみ)
_LINH = {_n("linh"), _n("lẻ")}

# スケール語 (降順)。({語形}, 乗数)
_SCALES: list[tuple[frozenset[str], int]] = [
    (frozenset({_n("vạn")}), 10_000),
    (frozenset({_n("nghìn"), _n("ngàn")}), 1_000),
    (frozenset({_n("trăm")}), 100),
]

_MULTIPLIERS = frozenset(
    {_MUOI10, _MUOI} | {w for words, _ in _SCALES for w in words}
)

# run 検出用の数詞語彙全体。
_NUMBER_WORDS = frozenset(
    set(_COEFF) | set(_UNIT_AFTER_MUOI) | set(_UNIT_AFTER_MUOI10)
    | set(_UNIT_AFTER_LINH) | {_ZERO} | _LINH | _MULTIPLIERS
)

_MAX_VALUE = 99_999

# 先頭曖昧係数語 (run パース失敗時の決定論的バックオフ対象。
# モジュールdocstring 変換条件2 参照。現在は năm=「年」のみ)。
_AMBIGUOUS_LEADING = frozenset({_n("năm")})


# --- 厳密パーサ (§5.5) ------------------------------------------------------------


def _parse_tens(tokens: list[str], is_remainder: bool) -> int | None:
    """十位以下 (0〜99) の厳密パース。パターン外は None (=run 全体が不変換)。

    is_remainder: スケール語の残余側 (右側) を解析中かどうか。残余側では
    裸の単位桁1語 ([d]) を認めない (linh/lẻ 必須。docstring の線引き参照)。
    """
    if not tokens:
        return 0
    if len(tokens) == 1:
        if tokens[0] == _MUOI10:
            return 10
        if tokens[0] in _COEFF:
            if is_remainder:
                return None  # hai nghìn năm / hai trăm ba は不変換
            return _COEFF[tokens[0]]
        return None
    if len(tokens) == 2:
        if tokens[0] == _MUOI10 and tokens[1] in _UNIT_AFTER_MUOI10:
            return 10 + _UNIT_AFTER_MUOI10[tokens[1]]
        if tokens[1] == _MUOI and tokens[0] in _TENS_COEFF:
            return _TENS_COEFF[tokens[0]] * 10
        return None
    if len(tokens) == 3:
        if (
            tokens[1] == _MUOI
            and tokens[0] in _TENS_COEFF
            and tokens[2] in _UNIT_AFTER_MUOI
        ):
            return _TENS_COEFF[tokens[0]] * 10 + _UNIT_AFTER_MUOI[tokens[2]]
        return None
    return None


def _parse_scaled(tokens: list[str], scale_idx: int, is_remainder: bool) -> int | None:
    """スケール語 (vạn/nghìn/ngàn/trăm) を降順に処理する再帰パーサ。"""
    if scale_idx == len(_SCALES):
        return _parse_tens(tokens, is_remainder)

    words, mult = _SCALES[scale_idx]
    pos = next((i for i, t in enumerate(tokens) if t in words), None)
    if pos is None:
        return _parse_scaled(tokens, scale_idx + 1, is_remainder)

    left, right = tokens[:pos], tokens[pos + 1:]

    # 係数 (必須)。không は trăm の係数としてのみ 0 (năm 位の飛び) を表す。
    if not left:
        return None
    if left == [_ZERO]:
        if mult != 100:
            return None
        coeff = 0
    else:
        coeff = _parse_scaled(left, scale_idx + 1, is_remainder=False)
        if coeff is None or coeff == 0:
            return None

    # 残余。linh/lẻ 始まりは「単位桁1語」のみ許す。
    if not right:
        rem = 0
    elif right[0] in _LINH:
        rest = right[1:]
        if len(rest) == 1 and rest[0] in _UNIT_AFTER_LINH:
            rem = _UNIT_AFTER_LINH[rest[0]]
        else:
            return None
    else:
        rem = _parse_scaled(right, scale_idx + 1, is_remainder=True)

    if rem is None or rem >= mult:
        return None
    return coeff * mult + rem


def _parse_number_run(tokens: list[str]) -> int | None:
    return _parse_scaled(tokens, 0, is_remainder=False)


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
            # 決定論的バックオフ (モジュールdocstring 変換条件2): 先頭の
            # 曖昧係数語 (năm=年) を1個だけ外して残りを再パースする。
            # "năm hai nghìn không trăm hai mươi sáu" → "năm 2026"。
            backoff = None
            if run[0] in _AMBIGUOUS_LEADING and len(run) > 1:
                rest = run[1:]
                if any(t in _MULTIPLIERS for t in rest):  # 変換条件1を再適用
                    backoff = _parse_number_run(rest)
            if backoff is not None and 0 <= backoff <= _MAX_VALUE:
                out.append(run[0])
                out.append(str(backoff))
            else:
                out.extend(run)  # 全か無か: パース失敗は run 全体を不変換
        i = j
    return " ".join(out)


# --- 記号除去 (語中アポストロフィ例外つき、en.py と同じ手法) -----------------------


def _strip_symbols_keep_apostrophe(text: str) -> str:
    """§5 手順3の句読点・記号除去 (P*/S*、語中アポストロフィは例外)。

    vi はラテン文字言語なので §5 手順3の例外 (word-internal apostrophes kept、
    ’→' 標準化) が適用される。
    """
    text = text.replace("’", "'")
    text = _WORD_INTERNAL_APOS_RE.sub(_APOS_PLACEHOLDER, text)
    text = "".join(
        " " if unicodedata.category(ch)[0] in ("P", "S") else ch for ch in text
    )
    return text.replace(_APOS_PLACEHOLDER, "'")


# --- メインパイプライン -----------------------------------------------------------


def normalize_vi(text: str) -> str:
    """PREREGISTRATION.md §5 のベトナム語正規化パイプライン (手順1-5)。"""
    # 1. Unicode NFKC (NFD入力の正準合成・全角英数字の統一を含む)
    text = unicodedata.normalize("NFKC", text)

    # 2. ケースフォールディング
    text = text.casefold()

    # 3. 桁区切り除去 (§5.5 vi の行: "." 千区切り、3桁グループ条件つき) —
    #    一般記号除去より前に実行する理由はモジュールdocstringを参照。
    text = _DIGIT_GROUP_SEP_RE.sub("", text)

    # 4. 記号・句読点の除去 (§5 手順3、P*/S*。語中アポストロフィは例外保持)
    text = _strip_symbols_keep_apostrophe(text)

    # 5. 空白畳み込み (§5 手順4)
    text = _WHITESPACE_RE.sub(" ", text).strip()

    # 6. 綴り数詞→数字 (§5.5)
    text = _convert_number_word_runs(text)

    return text


def tokenize_vi(text: str) -> list[str]:
    """WER計算用トークナイザ。§5.6 (vi) の指定どおり空白分割。

    en.py の tokenize_en と同じ流儀で、内部で normalize_vi() を適用してから
    分割する (生テキストを渡してよい)。
    """
    normalized = normalize_vi(text)
    if not normalized:
        return []
    return normalized.split(" ")
