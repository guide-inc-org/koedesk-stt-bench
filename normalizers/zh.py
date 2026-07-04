"""簡体中国語テキスト正規化 — PREREGISTRATION.md §5 (Normalization) の zh 部分を実装する。

対応する仕様セクション:
    §5 手順 1-4 (共通パイプライン: NFKC / ケースフォールド / 記号除去 / 空白畳み込み)
    §5.5       (数値等価性: 中国語数詞→算用数字、桁区切り除去)
    §5.6 (zh)  (「text is scored as given (simplified); if an engine emits
                traditional, OpenCC t2s conversion is applied」、
                WERトークナイザ = jieba、見出し指標 = CER)
    AMENDMENTS.md Amendment 1 (§5.4 改訂: zh は CER 計算前に全空白除去。
                凍結版=空白畳み込みのみ、との併記義務あり → 二値フラグで両実装)
    AMENDMENTS.md Amendment 3 (処理順の修正: True側の全空白除去は数値変換の
                **前** に適用する。下記【処理順 — Amendment 3】参照)

ピン留めバージョン (2026-07-05 時点でこの venv にインストール済み):
    jieba  == 0.42.1   (WERトークナイザ)
    OpenCC == 1.4.0    (繁体→簡体 t2s 変換)
    確認コマンド: `pip show jieba OpenCC`

--------------------------------------------------------------------------
【空白の扱い — ja.py「凍結仕様のあいまい性 #1」と同一の二値フラグ設計】

Amendment 1 (2026-07-05) により、空白を単語区切りに使わない言語 (ja/zh/th) は
CER 計算前に reference/hypothesis 双方から全空白を除去するのが改訂後ルール。
ただし同 Amendment とPREREGISTRATION §5 末尾の義務により、凍結版ルール
(空白の連続を単一スペースへ畳み込み+strip のみ) の数値も併記publishする。
よって ja.py と同型のフラグで両方を実装する:

    normalize_zh(text)                                   → 凍結版字義読み (既定値)
        空白の連続を単一スペースに畳み込み、前後をstripするのみ。
    normalize_zh(text, strip_all_whitespace_for_cer=True) → Amendment 1 改訂ルール
        上記に加え、残った空白も含めテキスト中の空白を全て除去する。

--------------------------------------------------------------------------
【処理順 — Amendment 3: 全空白除去は数値変換の前 (True 側のみ)】

Amendment 1 は「空白を除去してから CER を計算する」と定めた。当初実装は
全空白除去を数値変換の**後** (パイプライン末尾) に置いていたが、この順序は
分かち書きエンジン出力の数詞を断片化させる — 「两千 零 二十 六」が
2000 / 0 / 20 / 6 と独立に変換され、その後の全空白除去で「20000206」という
存在しない数を合成する。またブロックリスト保護も破られる (「万 一 下 雨」の
一→1 変換)。これは Amendment 1 の目的 (分かち書きという書式習慣を書き起こし
精度の指標から外す) を裏切る defect であり、Amendment 3 で全空白除去を
記号除去・空白畳み込みの直後 (数値変換の前) に移動した:

    normalize_zh("两千 零 二十 六", strip_all_whitespace_for_cer=True) → "2026"
    normalize_zh("万 一 下 雨",   strip_all_whitespace_for_cer=True) → "万一下雨"

False 側 (凍結字義モード) の処理順は一切変えない (従来どおり
"两千 零 二十 六" → "2000 0 20 6")。

裸の位取り文字ガード (d) との相互作用 (旧空白境界の引き継ぎ): 全空白除去で
新たに隣接した数詞runが誤変換されないよう、除去した空白の位置
(merged_space_boundaries) を変換器へ引き継ぎ、run を旧空白境界で分割した
各断片にガード (d) を適用する。FLEURS zh の「不足 4 万」は除去後「不足4万」
になるが、旧空白境界の断片「万」が裸の位取り文字なので run「4万」全体を
変換しない (空白なしの生入力「4万」は係数を持つ run として従来どおり 40000
へ変換される — ref/hyp 双方同一規則の宣言済み挙動)。なおこの境界情報は
生テキストへの一回適用で定義される: 正規化出力への再適用は境界情報を
持たないため、「数字+旧空白+位取り文字」クラスに限り True 側は固定点に
ならない (CER 計算は常に生テキストへの一回適用なので実害はない。
ガード (d) 導入時から存在する既知の性質)。

--------------------------------------------------------------------------
【OpenCC t2s の適用位置 — NFKC の後に適用する (採用理由の明記)】

§5.6 は「エンジンが繁体字を出力した場合 t2s を適用する」としか書いておらず、
共通パイプライン (手順1 NFKC) との順序を規定していない。本実装は
**手順1 NFKC の直後・他の全処理の前** に t2s を適用する。理由:

  (i)  NFKC を先にする理由: NFKC は CJK互換漢字 (CJK Compatibility
       Ideographs、例 U+F9F4) を統合漢字の正準コードポイントへ写像する。
       OpenCC の変換辞書は統合漢字を鍵にしているため、互換漢字のまま
       t2s に渡すと変換漏れが起きうる。NFKC→t2s の順ならこの取りこぼしがない。
       逆方向の心配は不要: t2s の出力 (簡体字) は統合漢字であり NFKC 不変
       なので、t2s の後に NFKC をやり直す必要はない。
  (ii) 他の全処理 (数値変換を含む) より前にする理由: 繁体字の数詞
       (萬/兩/貳 等のうち本実装の対象は 萬→万・兩→两) を先に簡体へ
       揃えておかないと、数値コンバータが繁体字用の文字集合を二重に
       持つ必要が生じる。t2s を先に置けばコンバータは簡体字のみを見ればよい。
  (iii) 「エンジンが繁体字を出力した場合」の判定は行わず **無条件に** t2s を
       適用する。簡体字入力に対する t2s は恒等変換 (no-op) なので、条件分岐
       (=繁体字判定器という新たな恣意的表面) を持ち込まずに仕様を満たせる。
       reference も同じパイプラインを通るため公平性も保たれる。

--------------------------------------------------------------------------
【§5.5 中国語数詞→算用数字 変換の保守的ルール】

対象範囲: 0〜99,999 の整数 (ja と同範囲)。変換対象の文字集合:
    〇 零 一 二 三 四 五 六 七 八 九 两 十 百 千 万

ja.py の kanji_to_arabic と共通する漢字が多いが、**ja.py を import せず
独立実装** する。言語ごとの規則差があるため (下記 两・零)、共有実装は
片言語の修正が他言語の凍結ルールを壊す事故の温床になる。

ja.py との規則差:

(a) 两 (=2) の扱い:
    中国語では単位の直前の「2」は 二 ではなく 两 が普通 (两千=2000、
    两万=20000、口語で 两百=200)。一方、単位を伴わない 两 は
    「两个人 (2人)」のような量詞前の用法のほか、
    「三两 (重さの単位・liǎng、約50g)」「两样 (異なる)」のような
    数値変換してはならない用法を持つ。構造的に区別する決定的規則:
        run 中の全ての 两 が直後に位取り単位 (十/百/千/万) を伴う場合のみ
        変換する。単独の 两・単位を伴わない 两 を含む run は変換しない。
    これにより 两千→2000 / 两万三千→23000 は変換され、
    两个人 / 三两 / 两样 は不変換で残る (ref/hyp 双方同一規則)。

(b) 零 の挿入規則:
    中国語は位が飛ぶとき明示的に 零 を挿入する正書法を持つ
    (一百零五=105、三万零五百=30500。日本語は 百五 と書き零を挿入しない)。
    位取り計算モードでは 零/〇 は「位の飛びの標識」であり値に寄与しないので
    読み飛ばす。ただし係数が既に積まれた状態での 零 (例: 三零百 のような
    非文) は解析不能として ValueError → run 全体を不変換で残す
    (ja.py の「1万万」フォールバックと同じ方針)。
    位取り文字を含まない run では ja 同様の桁読み (二〇二六→2026、
    二零二六→2026) として 零/〇 を数字 0 に写像する。

(c) 範囲チェック 0〜99,999 (ko.py の _MAX_VALUE 方式と同一):
    パース結果が 99,999 を超える run (十万=100,000、百万=10^6、千万=10^7、
    ASCII混在の 10万 等) は不変換で残す。§5.5 はコンバータの対象を
    「integers 0–99,999」と凍結しており、範囲の拡張は凍結後の規則追加に
    あたるため上限で切る (ref/hyp 双方同一規則)。副次効果として、
    慣用句「千万不要 (くれぐれも〜するな)」の 千万 と、概数「数百万」の
    百万 (数 は数詞文字集合外なので run は 百万 のみ) が自動的に不変換となる
    (ko.py が 천만에요 の 천만 を範囲チェックで自動除外したのと同型で、
    個別ブロックリスト不要)。

(d) 裸の位取り文字 run の不変換ガード (ko.py「単音節 run は不変換」相当):
    run が位取り文字 (十/百/千/万) のみで構成され係数 (数字文字・ASCII数字)
    を1つも持たない場合は不変換で残す。動機 (実測破損): FLEURS zh の参照文は
    「人口数量不足 4 万。」のように ASCII 数字と位取り文字を空白で分かち書き
    するパターンを含む。単独の 万 を 10000 へ変換すると、Amendment 1 の
    全空白除去後に直前の「4」と結合して「410000」という存在しない数を合成
    してしまう (run 検出は空白を跨がないため「4 万」を一体として 40000 に
    することもできない)。
    両論併記: ja.py は単独の 十/百/千/万 を 10/100/1000/10000 へ変換する
    (ja パイロット378発話でこの分かち書き破損パターンが観測されなかったため、
    ja では変換側が実測に即す)。zh は上記の実測破損を根拠に不変換側へ線を
    引く。トレードオフとして正当な単独用法 (十天=10日 の 十 等) も不変換に
    なるが、ref/hyp 双方に同一規則が適用される宣言済みノイズとして許容する
    (ko.py が単音節ガードで 십년 の 십 を諦めたのと同じ扱い)。
    なお「4万」(空白なしの混在 run) は係数を持つため従来どおり 40000 へ
    変換される。Amendment 3 (True側の全空白除去を数値変換より前に移動) の
    適用時は、除去した旧空白位置で run を断片に分割し、各断片にこのガードを
    適用する (「4 万」→「4万」でも断片「万」が裸なので不変換 — 上記
    【処理順 — Amendment 3】参照)。

アルゴリズム (zh_numerals_to_arabic) は ja.py の kanji_to_arabic と同構造:
  1. 数詞文字集合 (+ASCII数字) の最大連続 run を正規表現で検出。
  2. 万 を境に前後を分割し 前半*10000+後半 として合成 (3万3000 のような
     ASCII混在 run も同様)。
  3. 万 を含まない部分は位取り文字 (十/百/千) の有無で
     位取り計算 (三千五百=3500) / 桁読み (二〇二六=2026) を切替。
  4. 変換可否は run とその近傍文脈への明示的ブロックリストで判定
     (ja.py と同じ「構造規則ではなく語彙ブロックリスト」方式)。

  この保守的ルールで **意図的に変換しない** あいまいクラス
  (normalizers/test_zh.py で列挙・アサート):
    一起 (「一緒に」— 数とは独立に語彙化)
    一样 (「同じ」— 同上)
    一直 (「ずっと」— 同上)
    一些 (「いくつかの」— 同上)
    一切 (「すべて」— 同上)
    一般 (「普通の」— 同上)
    一点 (「少し」/時刻「1時」— 読みがあいまい)
    一定 (「必ず」— 語彙化)
    一共 (「合計で」— 語彙化) / 一边 (「〜しながら」— 語彙化)
    万一 (「もしも」— 慣用句。run 全体一致で個別ブロック)
    零食/零钱/零售/零件 (零 が「端数・こまごました」の意で語彙化した熟語)
    十分 (「非常に」の副詞。「10分」の意もあるがあいまいなため不変換 —
          副作用として 十分钟(10分間) も不変換で残る。ref/hyp 双方
          同一規則が適用されるため公平性は保たれる)
    两 単独 / 三两 (量詞前の两・重さ単位の两 — 構造規則 (a) で除外)
    千万 / 百万 / 十万 (範囲チェック (c) で除外 — 千万不要・数百万 を含む)
    十 / 百 / 千 / 万 単独 (裸の位取り文字 — ガード (d) で除外)

  既知の残存限界 (ja.py と同じ設計上のトレードオフ): 统一・唯一 のように
  **数詞の直前の文字** と結合して語彙化した熟語は、run+直後1文字の
  ブロックリストでは拾えない (统一→统1 と変換されてしまう)。ja.py が
  「統一」「一切」を既知の限界として許容したのと同じ扱いとし、実データで
  問題が確認された場合は前方文脈ブロックリストを Amendment 手続きで追加する
  (個別に結果を見て事後的に判断しない、という検証原則に従う)。

--------------------------------------------------------------------------
【桁区切り除去の順序】

ja.py「実装上の解釈が必要だった箇所 (a)」と同一: 数字に挟まれたカンマ
(, U+002C / ， U+FF0C — 後者はNFKCで前者に写像済み) の除去は一般記号除去
より前に行う。理由・唯一解である根拠は ja.py の当該節を参照。
"""

from __future__ import annotations

import re
import unicodedata

try:
    import jieba
except ImportError:  # pragma: no cover - jieba は venv に必須で入っている前提
    jieba = None

try:
    import opencc
except ImportError:  # pragma: no cover - OpenCC は venv に必須で入っている前提
    opencc = None


# --- 数詞の文字集合 (§5.5) -------------------------------------------------------

_DIGIT_MAP = {
    "〇": 0, "零": 0,
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9,
    "两": 2,  # 単位直前の係数としてのみ変換対象 (モジュールdocstring (a) 参照)
}
_UNIT_MAP = {"十": 10, "百": 100, "千": 1000}
_MYRIAD = "万"

_NUMKANJI_CHARS = "".join(_DIGIT_MAP) + "".join(_UNIT_MAP) + _MYRIAD
# ASCII数字も混在run (例: 3万3000) を拾うために文字クラスへ含める。
_NUMBER_RUN_RE = re.compile(f"[0-9{_NUMKANJI_CHARS}]+")

# §5.5 の対象範囲上限 (ko.py の _MAX_VALUE と同一。モジュールdocstring (c) 参照)。
_MAX_VALUE = 99_999

# 数詞のみで構成される慣用句のブロックリスト。run全体が完全一致した場合のみ
# 変換をスキップする (部分文字列としての出現は変換する)。
_IDIOM_BLOCKLIST = {"万一"}

# run (通常1文字) + 直後の1文字を連結した文字列が語彙化した語と完全一致する
# 場合に変換をスキップするブロックリスト。§5.5「idiomatic uses ... are left
# untouched」に対応する zh のあいまいクラス (test_zh.py で列挙)。
_LEXICALIZED_BLOCKLIST = {
    "一起", "一样", "一直", "一些", "一切", "一般", "一点", "一定",
    "一共", "一边",
    # 零 が「端数・こまごました」の意で語彙化した熟語 (零≠数値0):
    "零食", "零钱", "零售", "零件",
    # 十分 (「非常に」の副詞。10分=時間の意もあるがあいまいなため不変換。
    # トレードオフ: 十分钟(10分間) も run+次1文字が「十分」に一致するため
    # 不変換で残る — ref/hyp 双方同一規則なので公平性は保たれる):
    "十分",
}


def _parse_kanji_or_digit_span(part: str) -> int:
    """万を含まない (=既に分割済みの) 数詞文字列を整数へ変換する。

    ASCII数字だけの場合はそのまま int()。
    十/百/千 のいずれも含まなければ「桁読み」(1文字=1桁の連結) とみなす
    (例: 二〇二六 → "2026"、二零二六 → "2026")。
    十/百/千 を含む場合は位取り計算を行う (例: 三千五百 → 3500、
    一百零五 → 105、十 → 10)。零/〇 は位の飛びの標識として読み飛ばすが、
    係数が積まれた状態での零は非文なので ValueError (呼び出し側で
    不変換フォールバック)。
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
    pending = ""  # 単位の直前に置かれた係数 (ASCII digitと数詞1文字の混在を許容)
    for ch in part:
        if ch in ("零", "〇"):
            # 位の飛びの標識 (一百零五)。係数が積まれた状態 (三零百 等の非文)
            # は解析不能として不変換フォールバックへ。
            if pending:
                raise ValueError(f"unexpected 零 after coefficient in {part!r}")
            continue
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
    """万を含みうる完全な数詞run文字列を整数へ変換する (0〜99,999想定)。"""
    if _MYRIAD in run:
        before, _, after = run.partition(_MYRIAD)
        # 「万万」のような重複 (STTハルシネーション) は after に万が残り
        # _parse_kanji_or_digit_span 内の桁読み int() で ValueError になる。
        before_val = _parse_kanji_or_digit_span(before) if before else 1
        after_val = _parse_kanji_or_digit_span(after) if after else 0
        return before_val * 10000 + after_val
    return _parse_kanji_or_digit_span(run)


def _boundary_fragments(
    run: str, start: int, merged_space_boundaries: frozenset[int]
) -> list[str]:
    """run を「全空白除去で消えた旧空白位置」で分割した断片リストを返す。

    merged_space_boundaries は空白除去後テキストにおける旧空白位置の
    インデックス集合 (normalize_zh の True 側でのみ非空。モジュールdocstring
    【処理順 — Amendment 3】参照)。境界が run 内部になければ [run] を返す
    (False 側・生入力では常にこの経路 = 従来挙動と同一)。
    """
    cuts = sorted(
        b - start for b in merged_space_boundaries if start < b < start + len(run)
    )
    if not cuts:
        return [run]
    frags = []
    prev = 0
    for cut in cuts:
        frags.append(run[prev:cut])
        prev = cut
    frags.append(run[prev:])
    return frags


def _should_convert(
    s: str,
    start: int,
    end: int,
    merged_space_boundaries: frozenset[int] = frozenset(),
) -> bool:
    """run=s[start:end] を変換してよいかどうかを §5.5 の保守的ルールで判定する。

    ja.py と同じく「明示的な語彙ブロックリスト」方式 + zh 固有の 两 構造規則
    (モジュールdocstring (a))。直後漢字の一律ブロックを採用しない理由も
    ja.py と同一 (两千块→2000块 のような正当な変換まで壊れるため)。
    """
    run = s[start:end]

    if run in _IDIOM_BLOCKLIST:
        return False

    next_char = s[end] if end < len(s) else ""
    if (run + next_char) in _LEXICALIZED_BLOCKLIST:
        return False

    # 裸の位取り文字ガード (モジュールdocstring (d)): 位取り文字のみで係数を
    # 持たない run (十/百/千/万 単独、および 十万/千万 等の連結) は不変換。
    # FLEURS zh「不足 4 万」の 万→10000 変換が全空白除去後に 410000 を
    # 合成した実測破損への対処。Amendment 3 適用時 (True側) は run を旧空白
    # 境界で分割した各断片に同じガードを適用する (境界なしなら run 全体が
    # 唯一の断片 = 従来挙動と同一)。
    for frag in _boundary_fragments(run, start, merged_space_boundaries):
        if frag and all(c in _UNIT_MAP or c == _MYRIAD for c in frag):
            return False

    # 两 の構造規則: run 中の全ての 两 が直後に位取り単位を伴う場合のみ変換。
    # (两个人 の 两、三两 の 两 を除外する。詳細はモジュールdocstring (a))
    for i, ch in enumerate(run):
        if ch == "两":
            if i + 1 >= len(run) or run[i + 1] not in (_UNIT_MAP.keys() | {_MYRIAD}):
                return False
    return True


def zh_numerals_to_arabic(
    text: str, *, merged_space_boundaries: frozenset[int] = frozenset()
) -> str:
    """中国語数詞 (および数詞とASCII数字の混在表記) を算用数字へ変換する。

    0〜99,999 の整数を対象とする決定的コンバータ。変換方針・除外ルールの詳細は
    このモジュールのdocstring「§5.5 中国語数詞→算用数字 変換の保守的ルール」を参照。

    merged_space_boundaries: Amendment 3 の全空白除去 (True側) で消えた旧空白
    位置の集合。normalize_zh が内部で渡す (ガード (d) の断片適用に使用)。
    生テキストへ直接使う場合は省略でよい。
    """
    out = []
    last = 0
    for m in _NUMBER_RUN_RE.finditer(text):
        run = m.group(0)
        if not any(c in _NUMKANJI_CHARS for c in run):
            # ASCII数字のみのrunは変換対象がないのでスキップ (no-op)。
            continue
        start, end = m.start(), m.end()
        if not _should_convert(text, start, end, merged_space_boundaries):
            continue
        # 解析不能なrun (例: 万の重複「1万万」、非文の零位置) は §5.5 の方針
        # (曖昧・解析不能は触らない) どおり変換せずそのまま残す。ja.py の
        # gemini-2.5-flash「約1万万年前」実例と同じフォールバック。
        # ref/hyp双方に同一規則が適用されるため公平性は保たれる。
        try:
            value = _parse_number_run(run)
        except (ValueError, KeyError):
            continue
        if not (0 <= value <= _MAX_VALUE):
            # 範囲外 (十万=100,000、百万、千万、10万 等) は §5.5 の対象範囲
            # (0–99,999) 超過につき不変換 (モジュールdocstring (c) 参照)。
            continue
        out.append(text[last:start])
        out.append(str(value))
        last = end
    out.append(text[last:])
    return "".join(out)


# --- OpenCC t2s (§5.6) -----------------------------------------------------------

_T2S_CONVERTER = None


def _get_t2s():
    global _T2S_CONVERTER
    if _T2S_CONVERTER is None:
        if opencc is None:  # pragma: no cover
            raise RuntimeError(
                "opencc がインストールされていません。"
                "`pip install OpenCC` を実行してください "
                "(このモジュールは OpenCC==1.4.0 で検証済み)。"
            )
        _T2S_CONVERTER = opencc.OpenCC("t2s")
    return _T2S_CONVERTER


# --- 記号・桁区切り除去 -----------------------------------------------------------

# 数字に挟まれたカンマ (桁区切り) の除去。一般記号除去より前に実行する理由は
# ja.py モジュールdocstring「実装上の解釈が必要だった箇所 (a)」と同一。
# ，(U+FF0C) はNFKC (手順1) で , (U+002C) に写像済みだが防御的に両方含める。
_DIGIT_GROUP_SEP_RE = re.compile(r"(?<=[0-9])[,，](?=[0-9])")


def _remove_digit_group_separators(text: str) -> str:
    return _DIGIT_GROUP_SEP_RE.sub("", text)


def _remove_punctuation_and_symbols(text: str) -> str:
    """Unicode カテゴリ P* (punctuation) / S* (symbol) の文字を除去する。

    ja.py と同じく Whisper系正規化器
    (normalizers/vendor/whisper_normalizers/basic.py) に倣い、単語の意図しない
    融合を避けるためスペースに置換してから、後段の空白畳み込み (§5 手順4) に
    委ねる。中国語の句読点 (。，、！？「」《》等) は全て P*/S* に属する。
    """
    return "".join(
        " " if unicodedata.category(c)[0] in ("P", "S") else c for c in text
    )


def _strip_spaces_with_boundaries(text: str) -> tuple[str, frozenset[int]]:
    """全空白を除去し、除去後テキストにおける旧空白位置の集合を併せて返す。

    §5 手順4 (空白畳み込み) 適用後のテキストを前提とする (この時点で残る
    空白は単一の U+0020 のみ)。返す境界集合は zh_numerals_to_arabic の
    merged_space_boundaries に渡す (モジュールdocstring
    【処理順 — Amendment 3】参照)。
    """
    chars: list[str] = []
    boundaries: set[int] = set()
    for ch in text:
        if ch == " ":
            boundaries.add(len(chars))
        else:
            chars.append(ch)
    return "".join(chars), frozenset(boundaries)


def normalize_zh(text: str, *, strip_all_whitespace_for_cer: bool = False) -> str:
    """PREREGISTRATION.md §5 (+ Amendment 1/3) の簡体中国語正規化パイプライン。

    Args:
        text: 生テキスト (リファレンスまたはエンジン出力)。
        strip_all_whitespace_for_cer: False (既定) では §5.4 凍結版を字義通りに
            実装 (空白の連続を単一スペースへ畳み込み、前後をstripするのみ)。
            True では Amendment 1 の改訂ルール (さらに残った空白も全て除去)。
            Amendment 3 により、この全空白除去は数値変換より**前**に適用する。
            詳細はモジュールdocstring「空白の扱い」と
            【処理順 — Amendment 3】を参照。

    Returns:
        正規化済みテキスト。
    """
    # 1. Unicode NFKC (全角英数/互換漢字の統一を含む)
    text = unicodedata.normalize("NFKC", text)

    # 2. OpenCC t2s (§5.6) — 無条件適用 (簡体入力にはno-op)。NFKCの直後に
    #    置く理由はモジュールdocstring「OpenCC t2s の適用位置」を参照。
    text = _get_t2s().convert(text)

    # 3. ケースフォールド (漢字には影響しない。埋め込みLatin文字のみ影響)
    text = text.lower()

    # 4. 桁区切り除去 (§5.5) — 一般記号除去より前に実行。
    text = _remove_digit_group_separators(text)

    # 5. 記号・句読点の除去 (§5 手順3、カテゴリ P*/S*)
    text = _remove_punctuation_and_symbols(text)

    # 6. 空白畳み込み (§5 手順4 凍結版)
    text = re.sub(r"\s+", " ", text).strip()

    if strip_all_whitespace_for_cer:
        # Amendment 1 のオプトイン + Amendment 3: 全空白除去は数値変換の
        # **前** に適用する (分かち書き出力の数詞断片化・ブロックリスト
        # 突破を防ぐ)。除去した旧空白位置は境界集合として変換器へ引き継ぐ
        # (ガード (d) の断片適用。docstring【処理順 — Amendment 3】参照)。
        text, boundaries = _strip_spaces_with_boundaries(text)
        # 7. 中国語数詞→算用数字変換 (§5.5)
        text = zh_numerals_to_arabic(text, merged_space_boundaries=boundaries)
    else:
        # 7. 中国語数詞→算用数字変換 (§5.5) — False 側 (凍結字義モード) の
        #    処理順は Amendment 3 の対象外で一切変えない。
        text = zh_numerals_to_arabic(text)

    return text


# --- WERトークナイザ (§5.6: jieba) ------------------------------------------------


def tokenize_zh(text: str) -> list[str]:
    """WER計算用のトークナイザ。jieba (精確モード) のトークンリスト。

    §5.6 が指定する jieba (== 0.42.1 でピン留め) で実装している。
    呼び出し側は事前に normalize_zh() で正規化したテキスト
    (フラグ False 側=凍結版の出力) を渡すこと。

    jieba は入力中の空白をそのまま空白トークンとして返すため、空白のみの
    トークンは除外する (ja の fugashi が空白をトークン化しないのと挙動を
    揃える)。注意: jieba の分割自体は空白を語境界ヒントとして使うため、
    分かち書きされた入力とされていない入力でトークンの切れ目が変わりうる。
    WER は凍結版 (フラグ False 側) の出力に対して計算するのが正であり、
    Amendment 1 も CER のみを対象とする (WER は §5.4 凍結版のまま)。
    """
    if jieba is None:  # pragma: no cover
        raise RuntimeError(
            "jieba がインストールされていません。"
            "`pip install jieba` を実行してください "
            "(このモジュールは jieba==0.42.1 で検証済み)。"
        )
    return [tok for tok in jieba.lcut(text) if tok.strip()]


def cer_chars_zh(text: str) -> list[str]:
    """CER計算用の文字列。§5.6よりCERが中国語の見出し指標であり、そのトークン単位は
    「正規化済みテキストの文字列そのもの」である (追加の分割処理は不要)。

    呼び出し側は事前に normalize_zh() で正規化したテキストを渡すこと
    (見出しCERは Amendment 1 によりフラグ True 側の出力)。
    """
    return list(text)
