"""日本語テキスト正規化 — PREREGISTRATION.md §5 (Normalization) の日本語部分を実装する。

対応する仕様セクション:
    §5 手順 1-4 (共通パイプライン: NFKC / ケースフォールド / 記号除去 / 空白畳み込み)
    §5.5       (数値等価性: 漢数字→算用数字、桁区切り除去)
    §5.6 (ja)  (全角/半角統一はNFKCに委譲、長音記号統一、
                かな⇄漢字・カタカナ⇄ひらがな統一は行わない=既知の限界、
                WERトークナイザ = MeCab + UniDic)

ピン留めバージョン (2026-07-04 時点でこの venv にインストール済み):
    fugashi      == 1.5.2   (MeCabラッパー)
    unidic-lite  == 1.0.8   (UniDic 辞書、lite版)
    確認コマンド: `pip show fugashi unidic-lite`

--------------------------------------------------------------------------
【凍結仕様のあいまい性 #1 — 空白畳み込み vs 全除去】(タスク指示により明示的に両論併記)

§5.4 は「空白の連続を単一スペースに畳み込み、前後をstrip」としか書いておらず、
「単語間の空白を全て除去する」とは書いていない。これは英語のようなスペース区切り
言語を前提にした文言であり、日本語は本来スペース区切りを持たない言語である。

一方、パイロットで観測された事実: エンジン gemini-3.1-flash-lite は日本語出力を
分かち書き (「敵対 的 環境」のようにトークンごとにスペースを挿入) することがあり、
リファレンス側は当然スペースなし (「敵対的環境」) である。この場合、仕様文言を
字義通り実装 (畳み込みのみ) すると、エンジン側にだけ余分なスペース文字が残り、
CER (文字誤り率) が不当に悪化する — 純粋な書き起こし精度とは無関係なノイズで
ランキングが歪む。

どちらの読み方が「正しい」かは凍結仕様だけからは決定不能なので、本実装は
**両方**をコードに実装し、フラグで切り替える:

    normalize_ja(text)                                  → 文字通りの読み方 (既定値)
        空白の連続を単一スペースに畳み込み、前後をstripするのみ。
        単語間の単一スペースは残る。
    normalize_ja(text, strip_all_whitespace_for_cer=True) → 改訂読み (おそらくの追加修正)
        上記に加え、残った空白も含めテキスト中の空白を全て除去する。

パイロットスコアラーは両方の値を計算して併記する。どちらを本番の見出し指標に
採用するかは、この差異自体を含めて近藤さんへの報告事項とし、ここでは判定しない。

--------------------------------------------------------------------------
【実装上の解釈が必要だった箇所 — あいまい性ではなく、仕様の例を満たすための唯一解】

(a) 桁区切り除去 (§5.5) と記号除去 (§5 手順3) の順序:
    手順3は Unicode カテゴリ P*/S* の除去を先に行うと明記されているが、
    桁区切りのカンマ (Unicode category "Po", P*) を先に一般記号除去してしまうと
    「33,000」→「33 000」(カンマがスペースに変換される、Whisper系正規化器の
    標準的な実装がそうしている、normalizers/vendor/whisper_normalizers/basic.py
    参照) となり、後段でカンマが桁区切りだったと判別する手段がなくなる。
    仕様が明示する具体例「33,000→33000」を満たせるのはカンマ→空対応を桁区切り
    除去として先に (数字に挟まれたカンマに限定して) 行う場合のみなので、本実装は
    「数字に挟まれたカンマの除去」を一般記号除去より前に実行する。これは競合する
    複数の妥当な読みがあるわけではなく、仕様の具体例を満たす唯一の実装なので
    フラグ化はしていない。

(b) 長音記号統一 (§5.6) と記号除去 (§5 手順3) の順序:
    長音記号の紛らわしい異体字 (U+2010〜U+2015 各種ハイフン/ダッシュ、
    U+2212 MINUS SIGN 等) は Unicode category "Pd" (ダッシュ punctuation) であり
    P* に含まれるため、手順3を先に実行すると「統一」する前に消えてしまう。
    よって本実装は長音記号統一をNFKCの直後・記号除去の前に行う。
    ただし「かな連続の直後にあるダッシュ類のみ」を長音記号とみなす条件を課す
    (下記 _CHOUON_LOOKALIKES 参照) ことで、数字レンジのハイフン (25-30→25 30、
    §5.4 に明記) や英字語のハイフンを誤って長音記号化しない。

--------------------------------------------------------------------------
【§5.5 漢数字→算用数字 変換の保守的ルール】

対象範囲: 0〜99,999 の整数 (仕様どおり)。変換対象の文字集合:
    〇 零 一 二 三 四 五 六 七 八 九 十 百 千 万

アルゴリズム (kanji_to_arabic):
  1. 上記文字集合 (+ 変換済み判定用にASCII数字) からなる最大連続runを正規表現で
     検出する (例: 「三万三千」「3万3000」「二〇二六」「十」「百五」)。
  2. run に ASCII 数字と漢数字が混在する場合 (例: 3万3000) は「万」を境に
     前後を分割し、それぞれを再帰的に評価してから
     前半 * 10000 + 後半 として合成する。
  3. 「万」を含まない run は、十/百/千 のような位取り文字を含むかどうかで
     - 位取りあり (例: 三千五百, 十, 百五, 二十五): 標準的な位取り計算
       (単位の直前の数字を係数とし、無ければ暗黙の1とする)
     - 位取りなし (例: 二〇二六): 桁読み (1文字=1桁) として文字列連結
     のいずれかで評価する。
  4. 変換を行うかどうかは run の前後の文脈で判定する (=保守的除外ルール)。

     検討の末に採用しなかった案: 「run の直後が漢字なら一律変換しない」という
     構造的ルール。これは一見安全に見えるが、実際の書き起こしでは数字の直後に
     単位・助数詞の漢字が来るのがむしろ通常であり (例: 三万三千円、十五歳、
     三十分)、これらは一切あいまいではない正当な数値なので、一律ブロックすると
     ほとんど全ての実用的な数値変換が機能しなくなってしまう。

     採用したルール: 「あいまいクラスは網羅的な構造規則ではなく、明示的な
     単語ブロックリストで除外する」。具体的には:
     - run 全体が厳密に「万一」と一致する場合 → 変換しない
       (慣用句「まんいち」。数字漢数字のみで構成される慣用句のため、
       構造規則では区別不能なので個別にブロックリスト化)。
     - run (通常1文字) + 直後の1文字を連結した文字列が、以下の
       ブロックリストの語のいずれかと完全一致する場合 → 変換しない:
           一人 (助数詞「ひとり」の慣用読み)
           一つ (かな書き助数詞)
           一番 (「いちばん」— 数とは独立に語彙化した副詞/名詞)
           一緒 (「いっしょ」— 数とは独立に語彙化した名詞)
           一般 (「いっぱん」— 数とは独立に語彙化した名詞)
           二日 (日付「ふつか」/期間、あいまいな読みを持つため)
     - 上記いずれにも該当しなければ変換する。序数接頭辞「第」自体は文字列に
       残したまま、後続の数字部分のみを変換する (第二十→第20、第一→第1)。

  この保守的ルールで **意図的に変換しない** (=リファレンス・仮説側とも
  無加工のまま残す) あいまいクラス (normalizers/test_ja.py で列挙・アサート):
    一人 / ひとり (助数詞・かな書きは元々漢数字runにマッチしない)
    一つ (かな書き助数詞)
    一番 (「いちばん」慣用句/助数詞)
    一緒 (「いっしょ」慣用句)
    一般 (「いっぱん」慣用句)
    万一 (「まんいち」慣用句、数字漢数字のみで構成されるため明示的にブロックリスト)
    二日 (日付/期間の「ふつか」、あいまいなため明示的にブロックリスト)

  既知の残存限界 (単語ブロックリスト方式ゆえに拾いきれないケース、
  今回のテスト対象8クラスには含まれないため許容): 「統一」「一切」のような
  数字漢字を含む他の語彙化した熟語で、ブロックリストに未登録のもの。
  新たなあいまいクラスが実データで見つかった場合は _LEXICALIZED_BLOCKLIST
  に追記し、テストで列挙する運用とする (個別に結果を見て事後的に判断しない、
  という検証原則に従う)。
"""

from __future__ import annotations

import re
import unicodedata

try:
    import fugashi
except ImportError:  # pragma: no cover - fugashi は venv に必須で入っている前提
    fugashi = None


# --- 数字漢数字の文字集合 (§5.5) -------------------------------------------------

_DIGIT_MAP = {
    "〇": 0, "零": 0,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
}
_UNIT_MAP = {"十": 10, "百": 100, "千": 1000}
_MYRIAD = "万"

_NUMKANJI_CHARS = "".join(_DIGIT_MAP) + "".join(_UNIT_MAP) + _MYRIAD
# ASCII数字も混在run (例: 3万3000) を拾うために文字クラスへ含める。
_NUMBER_RUN_RE = re.compile(f"[0-9{_NUMKANJI_CHARS}]+")

# 数字漢数字のみで構成される慣用句のブロックリスト。run全体が完全一致した場合のみ
# 変換をスキップする (部分文字列としての出現、例: 十万一千=101000、は変換する)。
_IDIOM_BLOCKLIST = {"万一"}

# run (通常1文字) + 直後の1文字を連結した文字列が語彙化した慣用句/助数詞と
# 完全一致する場合に変換をスキップするブロックリスト。§5.5 が例示する
# 「ja counters like 一人/ひとり, idiomatic uses, dates」に対応する、
# 実際にテストで列挙される8クラスのうち構造的に検出可能な6語。
_LEXICALIZED_BLOCKLIST = {"一人", "一つ", "一番", "一緒", "一般", "二日"}


def _parse_kanji_or_digit_span(part: str) -> int:
    """万を含まない (=既に分割済みの) 数字文字列を整数へ変換する。

    ASCII数字だけの場合はそのまま int()。
    十/百/千 のいずれも含まなければ「桁読み」(1文字=1桁の連結) とみなす
    (例: 二〇二六 → "2026")。
    十/百/千 を含む場合は位取り計算を行う
    (例: 三千五百 → 3500、百五 → 105、十 → 10)。
    """
    if part == "":
        return 0
    if part.isdigit():
        return int(part)

    if not any(c in _UNIT_MAP for c in part):
        # 桁読み: 各文字を1桁の数字文字列に変換して連結する。
        digit_str = "".join(
            str(_DIGIT_MAP[c]) if c in _DIGIT_MAP else c for c in part
        )
        return int(digit_str)

    # 位取り計算。
    value = 0
    pending = ""  # 単位の直前に置かれた係数 (ASCII digitと漢数字1文字の混在を許容)
    for ch in part:
        if ch.isdigit():
            pending += ch
        elif ch in _DIGIT_MAP:
            pending += str(_DIGIT_MAP[ch])
        elif ch in _UNIT_MAP:
            coeff = int(pending) if pending else 1
            value += coeff * _UNIT_MAP[ch]
            pending = ""
    if pending:
        value += int(pending)
    return value


def _parse_number_run(run: str) -> int:
    """万を含みうる完全な数字run文字列を整数へ変換する (0〜99,999想定)。"""
    if _MYRIAD in run:
        before, _, after = run.partition(_MYRIAD)
        before_val = _parse_kanji_or_digit_span(before) if before else 1
        after_val = _parse_kanji_or_digit_span(after) if after else 0
        return before_val * 10000 + after_val
    return _parse_kanji_or_digit_span(run)


def _should_convert(s: str, start: int, end: int) -> bool:
    """run=s[start:end] を変換してよいかどうかを §5.5 の保守的ルールで判定する。

    構造規則 (「直後が漢字なら常にブロック」等) ではなく、明示的な語彙ブロック
    リストで判定する。理由はモジュールdocstring「§5.5 漢数字→算用数字
    変換の保守的ルール」の「検討の末に採用しなかった案」を参照
    (直後漢字の一律ブロックは 三万三千円→33000円 のような正当な変換まで
    壊してしまうため)。
    """
    run = s[start:end]

    if run in _IDIOM_BLOCKLIST:
        return False

    next_char = s[end] if end < len(s) else ""
    if (run + next_char) in _LEXICALIZED_BLOCKLIST:
        return False
    return True


def kanji_to_arabic(text: str) -> str:
    """漢数字 (および漢数字とASCII数字の混在表記) を算用数字へ変換する。

    0〜99,999 の整数を対象とする決定的コンバータ。変換方針・除外ルールの詳細は
    このモジュールのdocstring「§5.5 漢数字→算用数字 変換の保守的ルール」を参照。
    """
    out = []
    last = 0
    for m in _NUMBER_RUN_RE.finditer(text):
        run = m.group(0)
        if not any(c in _NUMKANJI_CHARS for c in run):
            # ASCII数字のみのrunは変換対象がないのでスキップ (no-op)。
            continue
        start, end = m.start(), m.end()
        if not _should_convert(text, start, end):
            continue
        # 解析不能なrun (例: STTハルシネーション「1万万」= 万の重複) は
        # §5.5の方針 (曖昧・解析不能は触らない) どおり変換せずそのまま残す。
        # パイロット実データで gemini-2.5-flash が「約1万万年前」を出力し
        # ValueErrorでja採点全体が落ちた実例への対処。ref/hyp双方に同一規則が
        # 適用されるため公平性は保たれる
        try:
            converted = str(_parse_number_run(run))
        except (ValueError, KeyError):
            continue
        out.append(text[last:start])
        out.append(converted)
        last = end
    out.append(text[last:])
    return "".join(out)


# --- 長音記号統一 (§5.6) ---------------------------------------------------------

# 長音記号の紛らわしい異体字候補。NFKC後、全角ハイフン(U+FF0D)は既にASCIIハイフン
# (U+002D) へ変換済みなので、ここにも含める。
_CHOUON_LOOKALIKES = "‐‑‒–—―−-"
_CHOUON_MARK = "ー"  # ー (KATAKANA-HIRAGANA PROLONGED SOUND MARK, 正)

_CHOUON_UNIFY_RE = re.compile(
    f"([぀-ゟ゠-ヿ{_CHOUON_MARK}])([{re.escape(_CHOUON_LOOKALIKES)}])"
)


def _unify_chouon(text: str) -> str:
    """かな (ひらがな/カタカナ) または既存の長音記号の直後にあるダッシュ類の
    異体字のみを、正規の長音記号 U+30FC へ変換する。

    数字レンジのハイフン (25-30、直前が数字なので対象外) や英字語のハイフン
    (AI-powered、直前がLatin文字なので対象外)、および漢数字の「一」
    (Han文字でありダッシュ類でもかな類でもないので、この関数の入力にも
    出力にも一切登場しない) には影響しない。
    """
    # ダッシュが連続する場合 (例: 長音記号2連続の異体字表記) にも対応するため
    # 変化がなくなるまで繰り返し適用する。
    prev = None
    while prev != text:
        prev = text
        text = _CHOUON_UNIFY_RE.sub(lambda m: m.group(1) + _CHOUON_MARK, text)
    return text


# --- 記号・桁区切り除去 -----------------------------------------------------------

# 数字に挟まれたカンマ (桁区切り) の除去。一般記号除去より前に実行する理由は
# モジュールdocstring「実装上の解釈が必要だった箇所 (a)」を参照。
_DIGIT_GROUP_SEP_RE = re.compile(r"(?<=[0-9])[,，](?=[0-9])")


def _remove_digit_group_separators(text: str) -> str:
    return _DIGIT_GROUP_SEP_RE.sub("", text)


def _remove_punctuation_and_symbols(text: str) -> str:
    """Unicode カテゴリ P* (punctuation) / S* (symbol) の文字を除去する。

    Whisper系正規化器 (normalizers/vendor/whisper_normalizers/basic.py) に倣い、
    単語の意図しない融合を避けるためスペースに置換してから、後段の空白畳み込み
    (§5 手順4) に委ねる。
    """
    return "".join(
        " " if unicodedata.category(c)[0] in ("P", "S") else c for c in text
    )


def normalize_ja(text: str, *, strip_all_whitespace_for_cer: bool = False) -> str:
    """PREREGISTRATION.md §5 の日本語正規化パイプライン。

    Args:
        text: 生テキスト (リファレンスまたはエンジン出力)。
        strip_all_whitespace_for_cer: False (既定) では §5.4 を文字通りに実装
            (空白の連続を単一スペースへ畳み込み、前後をstripするのみ)。
            True では、さらに残った空白も全て除去する (分かち書き出力への
            対抗策としての改訂読み。詳細はモジュールdocstring「凍結仕様の
            あいまい性 #1」を参照)。

    Returns:
        正規化済みテキスト。
    """
    # 1. Unicode NFKC (全角/半角統一を含む)
    text = unicodedata.normalize("NFKC", text)

    # 2. ケースフォールド (かな漢字には影響しない。埋め込みLatin文字のみ影響)
    text = text.lower()

    # 3. 長音記号の異体字統一 (§5.6) — 記号除去より前に実行する理由は
    #    モジュールdocstring「実装上の解釈が必要だった箇所 (b)」を参照。
    text = _unify_chouon(text)

    # 4. 桁区切り除去 (§5.5) — 一般記号除去より前に実行する理由は (a) を参照。
    text = _remove_digit_group_separators(text)

    # 5. 記号・句読点の除去 (§5 手順3、カテゴリ P*/S*)
    text = _remove_punctuation_and_symbols(text)

    # 6. 空白畳み込み (§5 手順4)
    text = re.sub(r"\s+", " ", text).strip()

    # 7. 漢数字→算用数字変換 (§5.5)
    text = kanji_to_arabic(text)

    # あいまい性#1のオプトイン: 空白を完全除去する改訂読み。
    if strip_all_whitespace_for_cer:
        text = re.sub(r"\s+", "", text)

    return text


# --- WERトークナイザ (§5.6: MeCab + UniDic) --------------------------------------

_TAGGER = None


def _get_tagger():
    global _TAGGER
    if _TAGGER is None:
        if fugashi is None:  # pragma: no cover
            raise RuntimeError(
                "fugashi がインストールされていません。"
                "`pip install fugashi unidic-lite` を実行してください "
                "(このモジュールは fugashi==1.5.2 / unidic-lite==1.0.8 で検証済み)。"
            )
        _TAGGER = fugashi.Tagger()
    return _TAGGER


def tokenize_ja(text: str) -> list[str]:
    """WER計算用のトークナイザ。fugashi (MeCab) + unidic-lite の表層形リスト。

    §5.6 が指定する「MeCab + UniDic」を fugashi (バインディング) +
    unidic-lite (辞書、pipで導入可能な軽量版UniDic) で実装している。
    呼び出し側は事前に normalize_ja() で正規化したテキストを渡すこと。
    """
    tagger = _get_tagger()
    return [str(word.surface) for word in tagger(text)]


def cer_chars_ja(text: str) -> list[str]:
    """CER計算用の文字列。§5.6よりCERが日本語の見出し指標であり、そのトークン単位は
    「正規化済みテキストの文字列そのもの」である (追加の分割処理は不要)。

    呼び出し側は事前に normalize_ja() で正規化したテキストを渡すこと。
    """
    return list(text)
