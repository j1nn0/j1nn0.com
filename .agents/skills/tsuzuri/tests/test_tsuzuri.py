"""CLI の記録形式と、失敗しても既存のバージョンを壊さない約束を確かめる。"""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "tsuzuri.py"
SPEC = importlib.util.spec_from_file_location("tsuzuri", SCRIPT)
tsuzuri = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tsuzuri)


# req が見出しの形を検査するので、試験の要件も `## <番号>. <項目名>` で書く
REQUIREMENTS = "## 1. 言いたいこと\n要件の1バージョン目\n"
DESIGN = "要件定義書: r001\n\n## p1 最初の段落の主張\n\n## p2 次の段落の主張\n"


def without_at(entries):
    """外した文の記録から時刻（at）を除く。時刻は実行のたびに変わるので、並びと移行先だけを比べる。"""
    return [{k: v for k, v in entry.items() if k != "at"} for entry in entries]


class TsuzuriTests(unittest.TestCase):
    """一時フォルダで CLI の入出力と保存結果を確かめる。"""

    def setUp(self):
        """ほかの記録や git 設定に依存しない作業場所を作る。"""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.document = self.directory / "文章.md"
        self.root = Path(str(self.document) + ".tsuzuri")
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        self.env["GIT_CONFIG_NOSYSTEM"] = "1"
        self.env["GIT_CONFIG_GLOBAL"] = os.devnull
        self.env["PYTHONDONTWRITEBYTECODE"] = "1"
        # init は作った記録を一覧に足すので、利用者の一覧（~/.config/tsuzuri）を書き換えないよう一時フォルダへ向ける
        self.env["TSUZURI_REGISTRY"] = str(self.directory / "records.json")
        self.cli("init", self.document)
        self.cli("req", self.root, input=REQUIREMENTS)

    def cli(self, *arguments, input=None, code=0):
        """実際のプロセスで終了コードとトレースバックの有無を検証する。"""
        result = subprocess.run([sys.executable, str(SCRIPT), *map(str, arguments)],
                                input=input, capture_output=True, text=True, env=self.env)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        if code == 2:
            self.assertTrue(result.stderr.strip())
        return result

    def tags(self, **changes):
        """呼び出しで変えたい文機能だけを置き換える。"""
        return {"relation": "順接", "importance": "核", "role": ["主張"],
                "technique": ["描写"], "place": "1. 言いたいこと", **changes}

    def load(self, relative):
        """確定したファイルを CLI と別に読む。"""
        return json.loads((self.root / relative).read_text(encoding="utf-8"))

    def store(self, relative, value):
        """アプリのコメントや、検査で見つける破損を模擬する。"""
        (self.root / relative).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")

    def sentence(self, text, *, tags=None, **memo_options):
        """メモから文を確定し、呼び出し元へ ID とバージョンを渡す。"""
        arguments = []
        for key, value in memo_options.items():
            arguments.extend(["--" + key, value])
        result = self.cli("memo", self.root, "--text", "これから書く", *arguments)
        sid, ver = result.stdout.split()
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--text", text,
                 "--tags", json.dumps(tags if tags is not None else self.tags()))
        return sid, ver

    def block(self, spec, text="", **memo_options):
        """メモからブロックを確定し、ID と版を返す。"""
        arguments = [] if "sid" in memo_options else ["--block"]
        for key, value in memo_options.items():
            arguments.extend(["--" + key, value])
        sid, ver = self.cli("memo", self.root, "--text", "置く狙い", *arguments).stdout.split()
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--block", json.dumps(spec),
                 "--text", text, "--tags", '{"place":"1. 言いたいこと"}')
        return sid, ver

    def test_write_requires_memo(self):
        """AI の文を先に確定する操作を拒む。"""
        result = self.cli("write", self.root, "--sid", "s0001", "--ver", "v001",
                          "--text", "先に書いた文。", "--tags", json.dumps(self.tags()), code=2)
        self.assertIn("メモ", result.stderr)
        self.assertFalse((self.root / "sentences/s0001/v001.json").exists())
        self.assertEqual(self.load("order.json")["order"], [])

    def test_write_refuses_existing_version(self):
        """確定済みの文とメモは、再実行しても変わらない。"""
        sid, ver = self.sentence("最初の文。")
        paths = [self.root / f"sentences/{sid}/{ver}{suffix}.json" for suffix in ("", "-memo")]
        previous = [path.read_bytes() for path in paths]
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--text", "上書き。",
                 "--tags", json.dumps(self.tags()), code=2)
        self.assertEqual([path.read_bytes() for path in paths], previous)

    def test_write_records_version_title(self):
        """タイトルは指定したときだけ残り、v002 以降で省くと警告し、長すぎるタイトルは拒む。"""
        sid, ver = self.sentence("最初の文。")
        self.assertNotIn("title", self.load(f"sentences/{sid}/{ver}.json"))
        _, second = self.cli("memo", self.root, "--sid", sid, "--text", "直す").stdout.split()
        self.cli("write", self.root, "--sid", sid, "--ver", second, "--text", "直した文。",
                 "--tags", json.dumps(self.tags()), "--title", "x" * (tsuzuri.TITLE_LIMIT + 1), code=2)
        result = self.cli("write", self.root, "--sid", sid, "--ver", second, "--text", "直した文。",
                          "--tags", json.dumps(self.tags()), "--title", " 語：試した→試行した ")
        self.assertNotIn("--title がありません", result.stderr)
        self.assertEqual(self.load(f"sentences/{sid}/{second}.json")["title"], "語：試した→試行した")
        self.assertEqual(json.loads(self.cli("show", self.root).stdout.splitlines()[0])["title"], "語：試した→試行した")
        _, third = self.cli("memo", self.root, "--sid", sid, "--text", "また直す").stdout.split()
        result = self.cli("write", self.root, "--sid", sid, "--ver", third, "--text", "また直した文。",
                          "--tags", json.dumps(self.tags()))
        self.assertIn("--title がありません", result.stderr)

    def test_export_paragraphs_and_latest_versions(self):
        """段落を空行で区切り、メモだけの次のバージョンは本文に出さない。"""
        self.sentence("一文目。", tags=self.tags(relation="段落の始まり"))
        self.sentence("二文目。")
        self.sentence("次の段落。", tags=self.tags(relation="段落の始まり"))
        self.sentence("改めた一文目。", sid="s0001")
        self.cli("memo", self.root, "--sid", "s0002", "--text", "まだ書いていない")
        self.cli("export", self.root)
        self.assertEqual((self.root / "text.md").read_text(encoding="utf-8"),
                         "改めた一文目。\n二文目。\n\n次の段落。\n")
        shown = [json.loads(line) for line in self.cli("show", self.root).stdout.splitlines()]
        self.assertEqual([(item["sid"], item["ver"]) for item in shown],
                         [("s0001", "v002"), ("s0002", "v001"), ("s0003", "v001")])
        self.assertEqual(set(shown[0]), {"sid", "ver", "para", "in", "text", "tags", "memo"})
        self.cli("check", self.root)

    def test_templates_overlay_user_folder_on_bundled(self):
        """同梱のテンプレートに利用者のものを重ね、同じ名前なら利用者のものを出す。無い名前は誤りにする。"""
        user = self.directory / "templates"
        user.mkdir()
        (user / "社内記事.md").write_text("# 社内記事\n社内の記事に使います。\n", encoding="utf-8")
        (user / "README.md").write_text("# README\n利用者の README のテンプレートです。\n", encoding="utf-8")
        self.env["TSUZURI_TEMPLATES"] = str(user)
        listed = {line.split("\t")[0]: line.split("\t")[1] for line in self.cli("templates").stdout.splitlines()}
        self.assertIn("ブログとエッセイ", listed)
        self.assertIn("仕事の報告と提案", listed)
        self.assertEqual(listed["社内記事"], "社内の記事に使います。")
        self.assertEqual(listed["README"], "利用者の README のテンプレートです。")
        self.assertIn("利用者の README のテンプレートです。", self.cli("templates", "README").stdout)
        self.cli("templates", "無いテンプレート", code=2)

    def test_words_reports_both_tables_on_latest_text_and_memo(self):
        """同梱の既定の校正辞書と利用者の校正辞書を重ねて、最新のバージョンの文・執筆意図・ブロックの字に当てる。直すのは書き手。"""
        user = self.directory / "words.tsv"
        user.write_text("# 利用者の校正辞書\n確かめ\t確認\t熟語寄り\n道具の欄\tサイドバー\n", encoding="utf-8")
        self.env["TSUZURI_WORDS"] = str(user)
        self.sentence("古い題の文。")
        self.sentence("道具の欄で確かめる。", sid="s0001")
        self.block({"kind": "heading", "level": 2}, "お題と窓口")
        out = self.cli("words", self.root).stdout
        # 最新の s0001 だけを見る。既定の辞書の「道具」と、利用者の辞書の「道具の欄」「確かめ」の両方が当たる
        self.assertNotIn("古い題", out)
        self.assertIn("s0001 v002 文: 「道具」→ ツール", out)
        self.assertIn("「道具の欄」→ サイドバー [利用者の校正辞書]", out)
        self.assertIn("「確かめ」→ 確認（熟語寄り）", out)
        # 「お題」と熟語の中の「窓」には当てない
        self.assertNotIn("b0001", out)
        self.assertIn("当たり 3 件", out)
        # 壊れた行は、どの表の何行目かを添えて止める（黙って飛ばすと直したつもりの語が漏れる）
        user.write_text("確かめ\n", encoding="utf-8")
        self.assertIn("words.tsv:1", self.cli("words", self.root, code=2).stderr)

    def test_retire_removes_sentence_and_keeps_reason(self):
        """外した文は本文から消え、中身と外した理由は記録に残る。理由の無い外し方と入れ物のブロックの外し方は断る。"""
        self.sentence("残す文。")
        self.sentence("重なった呼びかけ。")
        self.cli("retire", self.root, "--sid", "s0002", "--text", "s0001 と同じ呼びかけなので外す")
        order = self.load("order.json")
        self.assertEqual(order["order"], ["s0001"])
        self.assertEqual(without_at(order["retired"]), [{"sid": "s0002", "into": []}])
        self.assertTrue((self.root / "sentences/s0002/v001.json").is_file())
        review = self.load("reviews/rv0001.json")
        self.assertEqual((review["sid"], review["ver"], review["aspect"]), ("s0002", "v001", "削除"))
        self.cli("export", self.root)
        self.assertEqual((self.root / "text.md").read_text(encoding="utf-8"), "残す文。\n")
        self.cli("check", self.root)
        self.cli("retire", self.root, "--sid", "s0001", "--text", " ", code=2)
        container, _ = self.block({"kind": "list", "ordered": False})
        self.cli("retire", self.root, "--sid", container, "--text", "箇条書きを外す", code=2)

    def test_retire_removes_table_block_and_keeps_it_tracked(self):
        """表のブロックは外すと本文から消え、中身と理由は記録に残り、check も通る。"""
        self.sentence("前の文。")
        table, _ = self.block({"kind": "table"}, "| a | b |\n|---|---|\n| 1 | 2 |")
        self.sentence("後の文。")
        self.cli("retire", self.root, "--sid", table, "--text", "表を表示しない媒体のため箇条書きに置き換えた")
        order = self.load("order.json")
        self.assertNotIn(table, order["order"])
        self.assertEqual(without_at(order["retired"]), [{"sid": table, "into": []}])
        self.assertTrue((self.root / "blocks" / table / "v001.json").is_file())
        review = self.load("reviews/rv0001.json")
        self.assertEqual((review["sid"], review["aspect"]), (table, "削除"))
        self.cli("export", self.root)
        self.assertNotIn("| a |", (self.root / "text.md").read_text(encoding="utf-8"))
        self.cli("check", self.root)

    def test_load_lists_paragraphs_long_and_comma_heavy_sentences(self):
        """衛星が核より多い段落、目安より長い文、読点の多い文を挙げる。候補を出すだけで、終了コードは0。"""
        sat = self.tags(importance="衛星")
        self.sentence("核の文。")
        self.sentence("衛星の一つ目。", tags=sat)
        self.sentence("あ" * 61 + "。", tags=sat)
        self.sentence("読点が、多くて、長くて、読みにくい文。", tags=sat)
        out = self.cli("load", self.root).stdout
        self.assertIn("衛星が多い: 核 1・衛星 3（s0002 s0003 s0004）", out)
        self.assertIn("s0003 62字", out)
        self.assertNotIn("s0001 ", out.split("## 長い文")[1])
        self.assertIn("s0004 読点 3", out)

    def test_load_lists_connectives_with_relation(self):
        """接続語・接続助詞を含む文を、文機能の接続と並べて出す。主語の「が、」は拾わない。"""
        self.sentence("文章が意図からずれていても、どこでずれたかは分かりません。")
        self.sentence("そのため、先に書かせます。")
        self.sentence("AI が、文を書きます。")
        out = self.cli("load", self.root).stdout
        section = out.split("## 接続の確認")[1]
        self.assertIn("s0001 接続", section)
        self.assertIn("逆接・譲歩「ても、」", section)
        self.assertIn("s0002 接続", section)
        self.assertIn("順接・理由「そのため」", section)
        self.assertNotIn("s0003", section)

    def test_connectives_skip_listing_demo_and_copula_no_de(self):
        """「AでもBでもなく」の「でも、」と、「のである」「のです」の「ので」は接続として拾わない。"""
        connectives = lambda text: [kind for kind, _, _ in tsuzuri._connectives(text)]
        self.assertEqual(connectives("論点はその機能でも、一覧の署名の有無でもなく、点です。"), [])
        self.assertEqual(connectives("表現できるようになったのである。"), [])
        self.assertEqual(connectives("それは大事なのです。"), [])
        self.assertEqual(connectives("雨でも、行きます。"), ["逆接・譲歩"])
        self.assertEqual(connectives("あるので記録を残します。"), ["順接・理由"])

    def test_load_counts_visible_text_only(self):
        """長い文と読点は、HTML のタグ・リンクの URL・脚注の呼び出しを外した見える字で数える。"""
        self.assertEqual(tsuzuri._visible('<span style="color:#EF5350">**テト**</span>の[資料](https://example.com/a)と[^1]。'), "テトの資料と。")
        self.assertEqual(tsuzuri._visible('[[#真　==🔴テト==──嘘|本：テト]]と==🔵ROSE==と[[#Chorus]]'), "本：テトと🔵ROSEとChorus")
        self.sentence('<span style="color:#EF5350;white-space:nowrap"><i>テト</i></span>　<span style="color:#6E86FF;white-space:nowrap"><i>ROSE</i></span>。')
        section = self.cli("load", self.root).stdout.split("## 長い文")[1].split("\n## ")[0]
        self.assertNotIn("s0001", section)

    def test_load_lists_repeated_nouns_for_demonstratives(self):
        """並べた語を「その〜」で受け直す所と、同じ段落の直前の文と同じ主題で始まる文を、こそあど言葉の候補に挙げる。"""
        self.sentence("項目や段落を選ぶと、その項目や段落を担う文が並びます。")
        self.sentence("文を選ぶと、その文の執筆意図が出ます。")
        self.sentence("tsuzuri は執筆意図を書かせます。")
        self.sentence("tsuzuri は文機能を付けさせます。")
        self.sentence("ユーザーは文を読みます。")
        section = self.cli("load", self.root).stdout.split("## くり返す名詞")[1].split("##")[0]
        self.assertIn("s0001 並べた語を「その」で受け直している: 「その項目や段落」", section)
        self.assertIn("s0004 直前の文と同じ主題: 「tsuzuriは」", section)
        self.assertNotIn("s0002", section)
        self.assertNotIn("s0003", section)
        self.assertNotIn("s0005", section)

    def test_load_lists_topic_echoed_in_predicate(self):
        """主題の末尾の語を文末の「〜です」でもう一度言う文を挙げ、違う語で言い切る文は挙げない。"""
        self.sentence("決める順は、要件定義書、設計書、一文ずつの順です。")
        self.sentence("決める順は要件定義書から始めます。")
        self.sentence("この欄の名前は、画面の名前と同じです。")
        section = self.cli("load", self.root).stdout.split("## 主題と述語の同じ語")[1].split("##")[0]
        self.assertIn("s0001 「順は、…順です」", section)
        self.assertNotIn("s0002", section)
        self.assertNotIn("s0003", section)

    def test_load_lists_actor_shift_in_one_sentence(self):
        """動作を連ねて条件で受け、最後に別の主語を出す文を挙げ、条件だけでつなぐ文と助詞の「に、」の文は挙げない。"""
        self.sentence("書き上がった文章は閲覧アプリで開き、文を選ぶと、その文の執筆意図と文機能が右の詳細パネルに出ます。")
        self.sentence("書き上がった文章を閲覧アプリで開いて文を選ぶと、その文の執筆意図と文機能が右の詳細パネルに出ます。")
        self.sentence("見出しの下に、前の段落との関係と、その段落が担う項目の番号を書きます。")
        self.sentence("したがって、L を同じにすれば、明るさがそろった色を作れる。")
        self.sentence("直した文は AI が次に手本として読み、好みの語を校正辞書に、決まった構成をテンプレートに足しておけば、品質が高くなります。")
        section = self.cli("load", self.root).stdout.split("## 途中で変わる動作主")[1].split("##")[0]
        for sid in ("s0001", "s0005"):
            self.assertIn(sid, section)
        for sid in ("s0002", "s0003", "s0004"):
            self.assertNotIn(sid, section)

    def test_load_lists_heading_material(self):
        """見出しごとに、その下の核の文を並べ、衛星と次の見出しの下の文は入れない。タイトルは要件定義書の言いたいことと照らす。"""
        self.block({"kind": "heading", "level": 1}, "題")
        self.block({"kind": "heading", "level": 2}, "使い方")
        self.sentence("核の文。", tags={**self.tags(), "importance": "核"})
        self.sentence("衛星の文。", tags={**self.tags(), "importance": "衛星"})
        self.block({"kind": "heading", "level": 2}, "入れ方")
        self.sentence("次の節の核。", tags={**self.tags(), "importance": "核"})
        section = self.cli("load", self.root).stdout.split("## 見出しと、その下の主張と核")[1].split("\n## 接続")[0]
        usage = section.split("## 使い方")[1].split("## 入れ方")[0]
        self.assertIn("核 s0001: 核の文。", usage)
        self.assertNotIn("s0002", usage)
        self.assertNotIn("s0003", usage)
        self.assertIn("要件定義書 8. 言いたいこと", section.split("## 使い方")[0])

    def test_dictionary_rows_marks_source_and_broken_rows(self):
        """校正辞書の行に出どころを付け、壊れた行も止めずに誤りを付けて返す（アプリの一覧が1行の誤りで出なくなるのを避ける）。"""
        user = self.directory / "words.tsv"
        user.write_text("# 自分の辞書\n頼む\t依頼する\t文語で\n([\t壊れた形\n", encoding="utf-8")
        with patch.dict(os.environ, {"TSUZURI_WORDS": str(user)}):
            rows = tsuzuri.dictionary_rows()
        mine = [r for r in rows if r["source"] == "自分"]
        self.assertEqual((mine[0]["pattern"], mine[0]["to"], mine[0]["note"]), ("頼む", "依頼する", "文語で"))
        self.assertIn("正規表現", mine[1]["error"])
        self.assertTrue(any(r["source"] == "標準" for r in rows))

    def test_dictionary_rows_report_patterns_that_overflow_or_nest_too_deep(self):
        """繰り返しの数が大きすぎる形と入れ子の深すぎる形は、re.error でなく OverflowError・RecursionError になる。行の誤りとして返す。"""
        user = self.directory / "words.tsv"
        user.write_text("a{4294967296}\t直す先\n" + "(" * 1200 + ")" * 1200 + "\t直す先\n", encoding="utf-8")
        with patch.dict(os.environ, {"TSUZURI_WORDS": str(user)}):
            mine = [r for r in tsuzuri.dictionary_rows() if r["source"] == "自分"]
            with self.assertRaises(ValueError):
                tsuzuri._word_rules()
        self.assertEqual(len(mine), 2)
        self.assertTrue(all("正規表現" in r["error"] for r in mine))

    def test_dictionary_source_is_decided_by_path_not_folder_name(self):
        """利用者の辞書を references という名のフォルダに置いても「自分」と出し、UTF-8 で読めない辞書は誤りの行にする。"""
        folder = self.directory / "references"
        folder.mkdir()
        user = folder / "words.tsv"
        user.write_text("頼む\t依頼する\n", encoding="utf-8")
        with patch.dict(os.environ, {"TSUZURI_WORDS": str(user)}):
            self.assertIn(("頼む", "自分"), [(r["pattern"], r["source"]) for r in tsuzuri.dictionary_rows()])
        user.write_bytes("頼む\t依頼する\n".encode("cp932"))
        with patch.dict(os.environ, {"TSUZURI_WORDS": str(user)}):
            broken = [r for r in tsuzuri.dictionary_rows() if r["source"] == "自分"]
        self.assertEqual(len(broken), 1)
        self.assertIn("UTF-8", broken[0]["error"])

    def test_heading_material_leaves_out_footnote_sentences(self):
        """脚注の中の文は、核でも見出しの材料に入れない（本文の主張ではなく出典の書誌のため）。要件定義書が無いことと項目8が空なことを分けて示す。"""
        self.block({"kind": "heading", "level": 1}, "題")
        self.block({"kind": "heading", "level": 2}, "結果")
        self.sentence("本文の核。", tags={**self.tags(), "importance": "核"})
        note, _ = self.block({"kind": "footnote", "label": "x"})
        sid, ver = self.cli("memo", self.root, "--text", "出典を示す").stdout.split()
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--in", note, "--text", "脚注の核。",
                 "--tags", json.dumps({**self.tags(), "importance": "核"}))
        output = self.cli("load", self.root).stdout
        section = output.split("## 見出しと、その下の主張と核")[1].split("\n## 接続")[0]
        self.assertIn("本文の核。", section)
        self.assertNotIn("脚注の核。", section)
        # 試験の要件定義書は項目8を持たない。消すと「無い」の文言に変わる
        self.assertIn("（項目8が空）", section)
        import shutil
        shutil.rmtree(self.root / "requirements")
        self.assertIn("（要件定義書が無い）", self.cli("load", self.root).stdout)

    def test_comment_reopened_then_retired_is_resolved_only_after_reopening(self):
        """開き直した時刻より後に文を外したら、外したことで対応済みにする。時刻の無い開き直しと、真偽値の時刻は信じない。"""
        self.sentence("要らない文。")
        self.store("comments/c0001.json", {"sid": "s0001", "ver": "v001", "text": "開き直したあとに外した", "status": "open",
                                           "created_at": 1, "posted_latest": "v001", "reopened_at_ver": "v001", "reopened_at": 2})
        self.store("comments/c0002.json", {"sid": "s0001", "ver": "v001", "text": "時刻の無い開き直し", "status": "open",
                                           "created_at": 1, "posted_latest": "v001", "reopened_at_ver": "v001"})
        self.cli("retire", self.root, "--sid", "s0001", "--text", "読み手に要らない")
        by_text = {c["text"]: c for c in map(json.loads, self.cli("comments", self.root).stdout.splitlines())}
        self.assertEqual(by_text["開き直したあとに外した"]["addressed_by"], "retired")
        self.assertEqual(by_text["時刻の無い開き直し"]["status"], "open")
        self.assertEqual(by_text["開き直したあとに外した"]["note"], "本文から外した文へのコメント")
        order = self.load("order.json")
        order["retired"][0]["at"] = True
        self.store("order.json", order)
        by_text = {c["text"]: c for c in map(json.loads, self.cli("comments", self.root).stdout.splitlines())}
        self.assertEqual(by_text["開き直したあとに外した"]["status"], "open")

    def test_comment_addressed_by_a_new_version_keeps_that_version_after_retire(self):
        """新しいバージョンで対応済みになったコメントは、あとで文を外しても対応先をそのバージョンのまま保つ。"""
        self.sentence("元の文。")
        self.store("comments/c0001.json", {"sid": "s0001", "ver": "v001", "text": "直して", "status": "open",
                                           "created_at": 1, "posted_latest": "v001"})
        self.sentence("直した文。", sid="s0001")
        self.cli("retire", self.root, "--sid", "s0001", "--text", "不要")
        comment = json.loads(self.cli("comments", self.root).stdout.splitlines()[0])
        self.assertEqual((comment["status"], comment["addressed_by"]), ("resolved", "v002"))

    def test_checklist_needs_evidence_and_drops_confirmation_after_edits(self):
        """標準の確認項目は文の ID を添えた confirm で確認済みになり、本文が変わると「確認後に変更」に戻る。条件の語が無い項目は出さない。"""
        self.sentence("最初の文。")
        output = self.cli("checklist", self.root, code=1).stdout
        self.assertIn("標準 / 用語", output)
        self.cli("confirm", self.root, "--item", "用語", "--sids", "s9999", "--text", "読んだ", code=2)
        self.cli("confirm", self.root, "--item", "用語", "--sids", "s0001", "--text", "定義した語のまま")
        self.assertIn("[x] 標準 / 用語", self.cli("checklist", self.root, code=1).stdout)
        self.sentence("直した文。", sid="s0001")
        self.assertIn("[ ] 標準 / 用語: ", self.cli("checklist", self.root, code=1).stdout)
        self.assertIn("確認後に変更", self.cli("checklist", self.root, code=1).stdout)
        self.assertIn("確認項目が", self.cli("export", self.root).stderr)
        self.cli("check", self.root)
        # frontmatter（meta）を入れても、本文の確認は外れない
        self.cli("confirm", self.root, "--item", "用語", "--sids", "s0001", "--text", "直した文も読んだ")
        self.cli("meta", self.root, input="title: 題\n")
        self.assertIn("[x] 標準 / 用語", self.cli("checklist", self.root, code=1).stdout)

    def test_template_checklist_judges_chapter_previews_by_machine(self):
        """テンプレートの（判定: 章の予告）は、番号の付いた章の最後の文に予告が無いと不通過にする。最後の番号の章と脚注は数えない。"""
        folder = self.directory / "templates"
        folder.mkdir()
        (folder / "記事.md").write_text("# 記事\n試験用。\n\n## 確認項目\n\n- 章の予告: 予告がある（判定: 章の予告）\n", encoding="utf-8")
        self.env["TSUZURI_TEMPLATES"] = str(folder)
        self.cli("req", self.root, input="".join(f"## {n}. 項目{n}\n中身\n\n" for n in range(1, 9)) + "## 9. 文章の形\nテンプレート「記事」。文語の敬体\n")
        self.block({"kind": "heading", "level": 2}, "1. 背景")
        self.sentence("背景の文。")
        self.block({"kind": "heading", "level": 2}, "2. 仕組み")
        self.sentence("仕組みの文[^x]。")
        note, _ = self.block({"kind": "footnote", "label": "x"})
        sid, ver = self.cli("memo", self.root, "--text", "出典を示す").stdout.split()
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--in", note, "--text", "出典の書誌。次の章では使わない。",
                 "--tags", json.dumps(self.tags()))
        self.block({"kind": "heading", "level": 2}, "3. 結論")
        self.sentence("結論の文。")
        output = self.cli("checklist", self.root, code=1).stdout
        self.assertIn("不通過", output)
        self.assertIn("「1. 背景」", output)
        self.assertIn("「2. 仕組み」", output)
        self.assertNotIn("「3. 結論」", output)
        self.sentence("次の章では、仕組みを解説します。", after="s0001")
        self.sentence("最後の章では、結論を述べます。", after="s0002")   # 脚注のブロックの前に入る
        self.assertIn("[x] 記事 / 章の予告", self.cli("checklist", self.root, code=1).stdout)
        # 機械で判定する項目は、書き手の確認で代えられない
        self.assertIn("機械で判定", self.cli("confirm", self.root, "--item", "章の予告", "--sids", "s0001", "--text", "x", code=2).stderr)

    def test_load_lists_short_potential_forms_outside_code(self):
        """可能動詞の短い形（読める・開けます）は候補に出し、コードの中と、可能形でない「読めば」は出さない。"""
        self.sentence("一覧から開けます。")
        self.sentence("`読める` はコードの中。")
        self.sentence("読めば分かります。")
        section = self.cli("load", self.root).stdout.split("## 可能動詞の短い形")[1].split("\n## ")[0]
        self.assertIn("s0001 可能動詞の短い形「開け」", section)
        self.assertNotIn("s0002", section)
        self.assertNotIn("s0003", section)

    def test_confirm_requires_every_candidate_sentence(self):
        """（候補: 接続の確認）の項目は、load の候補の文を全部含めないと記録せず、足りない確認は「候補の確認が不足」と示す。"""
        self.sentence("雨が降ったため、試合は中止です。")
        self.sentence("ただし、明日は晴れます。")
        self.sentence("候補にならない文。")
        result = self.cli("confirm", self.root, "--item", "接続", "--sids", "s0001", "--text", "一部だけ", code=2)
        self.assertIn("s0002", result.stderr)
        self.assertIn("候補 2 文", self.cli("checklist", self.root, code=1).stdout)
        self.cli("confirm", self.root, "--item", "接続", "--sids", "s0001,s0002", "--text", "全件を読んだ")
        self.assertIn("[x] 標準 / 接続", self.cli("checklist", self.root, code=1).stdout)
        # あとで候補が増えたら、その文を読んでいない確認は確認済みにしない
        self.sentence("一方で、風は強いままです。")
        output = self.cli("checklist", self.root, code=1).stdout
        self.assertIn("候補の確認が不足", output)
        self.assertIn("s0004", output)

    def test_load_skips_mono_de_and_mono_ni(self):
        """「もので」「ものに」の「ので」「のに」は接続助詞として拾わない。"""
        self.sentence("ユーザーが書いたものと AI が書いたもので色が分かれます。")
        self.sentence("文そのものに言いたいことは欄へ書けます。")
        self.sentence("雨なので、傘を持ちます。")
        section = self.cli("load", self.root).stdout.split("## 接続の確認")[1]
        self.assertNotIn("s0001", section)
        self.assertNotIn("s0002", section)
        self.assertIn("s0003", section)

    def test_load_lists_each_satellite_for_the_reader_question(self):
        """衛星の文は1つずつ、執筆意図と並んで要否の問いの一覧に出る。核は出ない。"""
        self.sentence("核の文。")
        self.sentence("衛星の文。", tags={**self.tags(), "importance": "衛星"})
        section = self.cli("load", self.root).stdout.split("## 衛星の要否")[1].split("##")[0]
        self.assertIn("s0002", section)
        self.assertNotIn("s0001", section)

    def test_load_lists_paragraph_that_restates_earlier_ones(self):
        """前の段落の中心語を拾い集めただけの段落を、言い直しの候補に挙げる（cold-read.md の型5）。新しい話の段落は挙げない。"""
        start = self.tags(relation="段落の始まり")
        self.sentence("自宅のサーバーは毎晩、外付けのディスクと保管庫へ二重に保存する。", tags=start)
        self.sentence("外付けのディスクは手元に置き、保管庫は別の建物に置く。")
        self.sentence("保管庫へ送る前に暗号化し、鍵は別の場所に控える。", tags=start)
        self.sentence("暗号化の鍵を失うと、保管庫の中身は戻せない。")
        self.sentence("毎月一度、手元の端末で戻せるかを試験する。", tags=start)
        self.sentence("つまりサーバーは外付けのディスクと保管庫へ二重に保存し、保管庫へ送る前に暗号化し、鍵は別の場所に控える。", tags=start)
        self.sentence("外付けのディスクと保管庫と暗号化の鍵がそろえば、サーバーの中身は戻せる。")
        # 言い直しの節だけを見る（後ろの節には、同じ文が別の理由で出ることがある）
        out = self.cli("load", self.root).stdout.split("## 前の段落の言い直し")[1].split("\n## ")[0]
        self.assertIn("s0006〜s0007", out)
        self.assertNotIn("s0005", out)
        self.assertNotIn("s0003", out)

    def test_cold_builds_reader_prompt_without_intent(self):
        """読み手への指示は、要件定義書の3番と、文の ID 付きの本文だけで組む。執筆意図と文機能は入れない。"""
        self.cli("req", self.root, input="## 1. 依頼\n頼み\n\n## 2. 書く理由\n理由\n\n## 3. 公開する場所と読み手\n社内の板。読み手は新しく入った人。\n読み手は、この項目から、自分が読み手かを受け取る。\n")
        start = self.tags(relation="段落の始まり")
        self.sentence("最初の段落の文。", tags=start)
        self.block({"kind": "heading", "level": 2}, "見出し")
        self.sentence("次の段落の文。", tags=start)
        out = self.cli("cold", self.root).stdout
        self.assertIn("社内の板。読み手は新しく入った人。", out)
        self.assertNotIn("公開する場所と読み手", out.split("## あなたが演じる読み手")[1].split("## 検出するもの")[0])
        self.assertIn("[s0001] 最初の段落の文。", out)
        self.assertIn("[b0001] ## 見出し", out)
        self.assertIn("[s0002] 次の段落の文。", out)
        self.assertNotIn("これから書く", out)        # 執筆意図
        self.assertNotIn("この項目から", out)        # 要件の段階の問いの行
        self.assertNotIn("{{", out)
        self.cli("req", self.root, input="## 1. 依頼\n頼み\n")
        self.cli("cold", self.root, code=2)            # 3番の無い要件定義書では組めない

    def test_merge_and_split_preserve_origins(self):
        """統合と分割で元のバージョンを残し、移行先を配列で追える。"""
        for text in ("前。", "元の一文。", "元の二文。", "後。"):
            self.sentence(text)
        self.sentence("まとめた文。", **{"from": "s0002,s0003"})
        order = self.load("order.json")
        self.assertEqual(order["order"], ["s0001", "s0005", "s0004"])
        self.assertEqual(without_at(order["retired"]), [{"sid": "s0002", "into": ["s0005"]},
                                            {"sid": "s0003", "into": ["s0005"]}])
        self.sentence("分けた前半。", **{"from": "s0005"})
        self.sentence("分けた後半。", **{"from": "s0005"})
        order = self.load("order.json")
        self.assertEqual(order["order"], ["s0001", "s0006", "s0007", "s0004"])
        self.assertEqual(without_at(order["retired"])[-1], {"sid": "s0005", "into": ["s0006", "s0007"]})
        self.assertTrue((self.root / "sentences/s0002/v001.json").is_file())
        self.cli("check", self.root)

    def test_after_applies_only_when_written(self):
        """メモでは並びを変えず、確定した新しい文を指定位置へ入れる。"""
        self.sentence("最初。")
        self.sentence("最後。")
        result = self.cli("memo", self.root, "--text", "間に入れる", "--after", "s0001")
        self.assertEqual(result.stdout.strip(), "s0003 v001")
        self.assertEqual(self.load("order.json")["order"], ["s0001", "s0002"])
        self.cli("write", self.root, "--sid", "s0003", "--ver", "v001", "--text", "間。",
                 "--tags", json.dumps(self.tags()))
        self.assertEqual(self.load("order.json")["order"], ["s0001", "s0003", "s0002"])

    def test_pending_memo_refuses_another_memo_and_human_bypass(self):
        """書き直し中のメモを置き去りにする操作を拒む。"""
        self.sentence("最初。")
        self.cli("memo", self.root, "--sid", "s0001", "--text", "書き直す")
        before = (self.root / "sentences/s0001/v002-memo.json").read_bytes()
        result = self.cli("memo", self.root, "--sid", "s0001", "--text", "置き換える", code=2)
        self.assertIn("まだ文の無いメモ", result.stderr)
        self.cli("write", self.root, "--human", "--sid", "s0001", "--ver", "v003",
                 "--text", "飛ばす。", "--tags", json.dumps(self.tags()), code=2)
        self.assertEqual((self.root / "sentences/s0001/v002-memo.json").read_bytes(), before)

    def test_closed_vocabulary_and_open_vocabulary(self):
        """閉じた欄は拒み、役割と技法の未知語は警告して記録する。"""
        self.cli("memo", self.root, "--text", "文機能を付ける")
        for field in ("relation", "importance"):
            with self.subTest(field=field):
                self.cli("write", self.root, "--sid", "s0001", "--ver", "v001",
                         "--text", "本文。", "--tags", json.dumps(self.tags(**{field: "未知語"})), code=2)
        result = self.cli("write", self.root, "--sid", "s0001", "--ver", "v001", "--text", "本文。",
                          "--tags", json.dumps(self.tags(role=["新しい役割"], technique=["新しい技法"])))
        self.assertIn("警告: tags.role", result.stderr)
        self.assertIn("警告: tags.technique", result.stderr)
        self.cli("check", self.root)

    def test_many_roles_warn_but_record(self):
        """説明文の役割が3つ以上なら分けられないかを警告し、2つまでは警告しない。どちらも記録はする。"""
        self.cli("memo", self.root, "--text", "二つの働き")
        two = self.cli("write", self.root, "--sid", "s0001", "--ver", "v001", "--text", "だから、こうすべきだ。",
                       "--tags", json.dumps(self.tags(role=["主張", "理由"])))
        self.assertNotIn("役割が3つ以上", two.stderr)
        self.cli("memo", self.root, "--text", "三つの働き")
        three = self.cli("write", self.root, "--sid", "s0002", "--ver", "v001", "--text", "調べると良く、だからこうすべきだ。",
                         "--tags", json.dumps(self.tags(role=["主張", "理由", "根拠"])))
        self.assertIn("役割が3つ以上あります", three.stderr)
        self.assertEqual(self.load("sentences/s0002/v001.json")["tags"]["role"], ["主張", "理由", "根拠"])

    def test_technique_from_other_genre_warns(self):
        """説明文の役割に小説の工夫、小説の役割に説明文の工夫が付いたら警告し、合っていれば警告しない。"""
        self.cli("memo", self.root, "--text", "取り違え")
        wrong = self.cli("write", self.root, "--sid", "s0001", "--ver", "v001", "--text", "こうすべきだ。",
                         "--tags", json.dumps(self.tags(role=["主張"], technique=["文長を揺らす"])))
        self.assertIn("「文長を揺らす」は小説の工夫です", wrong.stderr)
        self.cli("memo", self.root, "--text", "逆の取り違え")
        reverse = self.cli("write", self.root, "--sid", "s0002", "--ver", "v001", "--text", "彼は黙った。",
                           "--tags", json.dumps(self.tags(role=["外面", "語り"], technique=["譲歩"])))
        self.assertIn("「譲歩」は説明文の工夫です", reverse.stderr)
        self.cli("memo", self.root, "--text", "合っている")
        fine = self.cli("write", self.root, "--sid", "s0003", "--ver", "v001", "--text", "もちろん大事だが、こうだ。",
                        "--tags", json.dumps(self.tags(role=["主張"], technique=["譲歩"])))
        self.assertNotIn("工夫です", fine.stderr)

    def test_custom_vocabulary(self):
        """利用者が足した関係と役割を認める。"""
        self.store("vocab.json", {"relation": ["応答"], "role": ["案内"]})
        self.sentence("答え。", tags=self.tags(relation="応答", role=["案内"]))
        self.cli("check", self.root)

    def test_bad_tags_and_ids_do_not_write(self):
        """外から渡された文機能と ID を保存前に検証する。"""
        self.cli("memo", self.root, "--text", "本文の予定")
        bad_tags = ["{", "[]", json.dumps(self.tags(role="主張")),
                    json.dumps(self.tags(place="")), json.dumps(self.tags(technique=[1]))]
        for tags in bad_tags:
            with self.subTest(tags=tags):
                self.cli("write", self.root, "--sid", "s0001", "--ver", "v001",
                         "--text", "本文。", "--tags", tags, code=2)
        for sid in ("../outside", "s0000", "s1", "s00001"):
            with self.subTest(sid=sid):
                self.cli("write", self.root, "--human", "--sid", sid,
                         "--text", "本文。", "--tags", json.dumps(self.tags()), code=2)
        self.assertFalse((self.root / "sentences/s0001/v001.json").exists())

    def test_requirements_versions_and_deviation(self):
        """新旧の要件を残し、照らしたバージョンとずれを文に記録する。"""
        source = self.directory / "要件.md"
        source.write_text("## 1. 言いたいこと\n新しい要件\n", encoding="utf-8")
        self.assertEqual(self.cli("req", self.root, "--file", source).stdout.strip(), "r002")
        self.cli("memo", self.root, "--text", "旧要件に照らす")
        self.cli("write", self.root, "--sid", "s0001", "--ver", "v001", "--text", "本文。",
                 "--tags", json.dumps(self.tags()), "--requirements", "r999", code=2)
        self.cli("write", self.root, "--sid", "s0001", "--ver", "v001", "--text", "本文。",
                 "--tags", json.dumps(self.tags()), "--requirements", "r001", "--deviation", "予定を改めた")
        first = self.load("sentences/s0001/v001.json")
        self.assertEqual(first["requirements"], "r001")
        self.assertEqual(first["deviation"], "予定を改めた")
        self.assertIsInstance(first["memo_at"], int)
        self.assertLessEqual(first["memo_at"], first["written_at"])
        self.assertEqual((self.root / "requirements/r001.md").read_text(encoding="utf-8"), REQUIREMENTS)
        sid, ver = self.sentence("新要件の文。")
        self.assertEqual(self.load(f"sentences/{sid}/{ver}.json")["requirements"], "r002")

    def test_human_auto_ids_and_rewrite(self):
        """人の文はメモを要求せず、ID と次のバージョンを自動で割り当てる。"""
        arguments = ["write", self.root, "--human", "--text", "人が書いた。", "--tags", json.dumps(self.tags())]
        self.assertEqual(self.cli(*arguments).stdout.strip(), "s0001 v001")
        self.assertEqual(self.cli(*arguments, "--sid", "s0001").stdout.strip(), "s0001 v002")
        self.assertEqual(self.cli(*arguments).stdout.strip(), "s0002 v001")
        sentence = self.load("sentences/s0001/v002.json")
        self.assertEqual(sentence["source"], "human")
        self.assertIsNone(sentence["memo_at"])
        self.cli("check", self.root)

    def test_human_sentence_takes_only_an_inferred_memo(self):
        """人の文は推測の執筆意図（memo --inferred）を受け取り、出どころを取り違えたメモは拒む（ADR-0002）。"""
        human = ["write", self.root, "--human", "--text", "人が書いた。", "--tags", json.dumps(self.tags())]
        self.assertEqual(self.cli("memo", self.root, "--inferred", "--text", "推測した意図").stdout.strip(), "s0001 v001")
        # ID を省いても、推測の執筆意図だけを先に書いた文を受け取る
        self.assertEqual(self.cli(*human).stdout.strip(), "s0001 v001")
        self.assertEqual(self.load("sentences/s0001/v001-memo.json")["by"], "inferred")
        self.assertIsInstance(self.load("sentences/s0001/v001.json")["memo_at"], int)
        self.assertNotIn("推測した執筆意図がありません", self.cli("check", self.root).stdout)
        # 人の文に AI の執筆意図、AI の文に推測の執筆意図は付けられない
        self.cli("memo", self.root, "--text", "AI の意図")
        self.assertIn("memo --inferred", self.cli(*human, "--sid", "s0002", code=2).stderr)
        self.cli("write", self.root, "--sid", "s0002", "--ver", "v001", "--text", "AI の文。", "--tags", json.dumps(self.tags()))
        self.cli("memo", self.root, "--inferred", "--sid", "s0002", "--text", "推測")
        self.cli("write", self.root, "--sid", "s0002", "--ver", "v002", "--text", "AI の文。", "--tags", json.dumps(self.tags()), code=2)
        self.cli("memo", self.root, "--inferred", "--block", "--text", "箱", code=2)

    def test_human_sentence_takes_a_reported_memo(self):
        """ほかのチャット AI が申告した執筆意図は by: reported で残し、推測と同時には付けられない。"""
        self.cli("memo", self.root, "--reported", "--text", "書いた AI の申告")
        self.cli("write", self.root, "--human", "--text", "人の文。", "--tags", json.dumps(self.tags()))
        self.assertEqual(self.load("sentences/s0001/v001-memo.json")["by"], "reported")
        self.assertNotIn("執筆意図がありません", self.cli("check", self.root).stdout)
        self.cli("memo", self.root, "--reported", "--inferred", "--text", "両方", code=2)

    def test_pack_and_unpack_share_one_record(self):
        """記録と文書を1つの .tsz にまとめ、展開してライブラリに足す。外へ出る名前や2つ目の記録は何も書かずに拒む。"""
        self.sentence("本文。")
        self.cli("export", self.root)
        self.document.write_text("本文。\n", encoding="utf-8")
        packed = self.directory / "共有.tsz"
        self.cli("pack", self.root, "--out", packed)
        target = self.directory / "受け取り"
        target.mkdir()
        self.cli("unpack", packed, "--dir", target)
        self.assertTrue((target / "文章.md.tsuzuri" / "order.json").is_file())
        self.assertEqual((target / "文章.md").read_text(encoding="utf-8"), "本文。\n")
        self.cli("check", target / "文章.md.tsuzuri")
        self.cli("unpack", packed, "--dir", target, code=2)
        bad = self.directory / "bad.tsz"
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("a.md.tsuzuri/order.json", "{}")
            archive.writestr("a.md.tsuzuri/../../evil.txt", "x")
        self.cli("unpack", bad, "--dir", target, code=2)
        self.assertFalse((self.directory / "evil.txt").exists())

    def _tsz(self, name, files, stored=False):
        """名前と中身の組から .tsz を作る。"""
        path = self.directory / name
        with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED) as archive:
            for entry, data in files:
                archive.writestr(entry, data)
        return path

    def test_unpack_rejects_unsafe_names_and_leaves_nothing(self):
        """隠しファイルの名前・大文字小文字だけ違う名前・途中で壊れた中身・リンクの置かれた名前は、展開先に何も残さずに拒む。"""
        target = self.directory / "受け取り"
        target.mkdir()
        order = json.dumps({"document": "x", "order": [], "retired": []})
        cases = [
            self._tsz("dot.tsz", [(".bashrc.tsuzuri/order.json", order), (".bashrc", "echo")]),
            self._tsz("case.tsz", [("a.md.tsuzuri/order.json", order), ("a.md.tsuzuri/Order.json", order)]),
            self._tsz("dir.tsz", [("a.md.tsuzuri/order.json", order), ("a.md/x", "y")]),
            self._tsz("ctrl.tsz", [("a.md.tsuzuri/order.json", order), ("a.md.tsuzuri/\x1b[2J", "y")]),
            self._tsz("noorder.tsz", [("a.md.tsuzuri/x.json", "{}")]),
        ]
        link = self.directory / "link.tsz"
        with zipfile.ZipFile(link, "w") as archive:
            archive.writestr("a.md.tsuzuri/order.json", order)
            info = zipfile.ZipInfo("a.md.tsuzuri/x.json")
            info.create_system, info.external_attr = 3, (0o120777 << 16)
            archive.writestr(info, "/etc/passwd")
        cases.append(link)
        # 2つ目のファイルの中身を壊す（CRC が合わず、1つ目を書いたあとで止まる）
        broken = self._tsz("broken.tsz", [("a.md.tsuzuri/order.json", order), ("a.md", "本文" * 50)], stored=True)
        data = bytearray(broken.read_bytes())
        at = data.index("本文".encode("utf-8") * 2)
        data[at] ^= 0xFF
        broken.write_bytes(bytes(data))
        cases.append(broken)
        for case in cases:
            with self.subTest(case=case.name):
                self.cli("unpack", case, "--dir", target, code=2)
                self.assertEqual(sorted(os.listdir(target)), [])
        # 記録の名前に、壊れたリンク（リンク先が無い）が置いてあっても書かない
        os.symlink(self.directory / "どこか", target / "a.md.tsuzuri")
        good = self._tsz("good.tsz", [("a.md.tsuzuri/order.json", order), ("a.md", "本文")])
        self.cli("unpack", good, "--dir", target, code=2)
        self.assertFalse((self.directory / "どこか").exists())

    def test_unpack_marks_received_and_pack_hides_local_path(self):
        """渡す order.json の文書の場所は名前だけにし、受け取った記録は展開先の場所と received の印を持ち、手本に混ざらない。"""
        self.sentence("本文。")
        self.document.write_text("本文。\n", encoding="utf-8")
        packed = self.directory / "共有.tsz"
        self.cli("pack", self.root, "--out", packed)
        with zipfile.ZipFile(packed) as archive:
            self.assertEqual(json.loads(archive.read("文章.md.tsuzuri/order.json"))["document"], "文章.md")
        target = self.directory / "受け取り"
        target.mkdir()
        self.cli("unpack", packed, "--dir", target)
        order = json.loads((target / "文章.md.tsuzuri" / "order.json").read_text(encoding="utf-8"))
        self.assertEqual((order["document"], order["received"]), (str(target.resolve() / "文章.md"), True))
        self.assertFalse(any(name.startswith(".tsz-") for name in os.listdir(target)))
        self.cli("pack", self.root, "--out", self.document, code=2)   # 文書そのものへは書き出さない
        self.assertEqual(self.document.read_text(encoding="utf-8"), "本文。\n")
        # 文書がリンクなら、リンク先の中身を入れない
        secret = self.directory / "secret.txt"
        secret.write_text("秘密", encoding="utf-8")
        self.document.unlink()
        os.symlink(secret, self.document)
        self.cli("pack", self.root, "--out", packed)
        with zipfile.ZipFile(packed) as archive:
            self.assertNotIn("文章.md", archive.namelist())

    def test_check_counts_human_sentences_without_inferred_memo(self):
        """推測の執筆意図より前の人の文は、誤りにせず数を知らせる。"""
        self.cli("write", self.root, "--human", "--text", "古い人の文。", "--tags", json.dumps(self.tags()))
        result = self.cli("check", self.root)
        self.assertIn("人の文 1 文のうち 1 文に、推測か申告の執筆意図がありません", result.stdout)

    def test_review_requires_confirmed_version(self):
        """指摘は確定した対象にだけ残し、前の指摘を上書きしない。"""
        arguments = ["review", self.root, "--sid", "s0001", "--ver", "v001",
                     "--aspect", "文機能の真偽", "--text", "役割を確かめる"]
        self.cli(*arguments, code=2)
        self.sentence("本文。")
        self.assertEqual(self.cli(*arguments).stdout.strip(), "rv0001")
        self.assertEqual(self.cli(*arguments).stdout.strip(), "rv0002")
        self.assertEqual(self.load("reviews/rv0001.json")["aspect"], "文機能の真偽")

    def test_comments_current_retired_orphan_and_broken(self):
        """コメントの元の参照先を保ち、今の本文と注記を添える。"""
        self.sentence("前の本文。")
        self.store("comments/current.json", {"sid": "s0001", "ver": "v001", "text": "直して"})
        self.sentence("今の本文。", sid="s0001")
        current = json.loads(self.cli("comments", self.root).stdout)
        self.assertEqual(current["current_text"], "今の本文。")
        self.assertIsNone(current["note"])
        self.sentence("移行先。", **{"from": "s0001"})
        self.store("comments/orphan.json", {"sid": "s9999", "ver": "v001", "text": "どこ？"})
        self.store("comments/version.json", {"sid": "s0002", "ver": "v999", "text": "バージョンが無い"})
        (self.root / "comments/broken.json").write_text("{", encoding="utf-8")
        previous = {path.name: path.read_bytes() for path in (self.root / "comments").iterdir()}
        comments = [json.loads(line) for line in self.cli("comments", self.root).stdout.splitlines()]
        by_text = {item.get("text"): item for item in comments}
        self.assertEqual(by_text["直して"]["note"], "置き換えられた元の文へのコメント")
        self.assertEqual(by_text["どこ？"]["note"], "行き先の無いコメント")
        self.assertEqual(by_text["バージョンが無い"]["current_text"], "移行先。")
        checked = self.cli("check", self.root, code=1)
        self.assertIn("壊れた JSON のコメント", checked.stdout)
        self.assertIn("行き先の無いコメント", checked.stdout)
        self.assertEqual({path.name: path.read_bytes() for path in (self.root / "comments").iterdir()}, previous)

    def test_comment_on_retired_sentence_is_resolved(self):
        """外した文へのコメントは、文を外したことで対応済みになる。アプリで開き直したものは開いたまま。"""
        self.sentence("要らない文。")
        self.sentence("残る文。")
        self.store("comments/c0001.json", {"sid": "s0001", "ver": "v001", "text": "この一文いらない", "status": "open"})
        self.store("comments/c0002.json", {"sid": "s0001", "ver": "v001", "text": "やっぱり戻して", "status": "open", "reopened_at_ver": "v001"})
        self.cli("retire", self.root, "--sid", "s0001", "--text", "読み手に要らない")
        by_text = {c["text"]: c for c in map(json.loads, self.cli("comments", self.root).stdout.splitlines())}
        self.assertEqual(by_text["この一文いらない"]["status"], "resolved")
        self.assertEqual(by_text["この一文いらない"]["addressed_by"], "retired")
        self.assertEqual(by_text["やっぱり戻して"]["status"], "open")
        # 投稿時の最新を持つコメントも、外す前に付いたものは対応済み。外したあとに付いたものは開いたまま
        self.sentence("分ける文。")
        self.store("comments/c0003.json", {"sid": "s0003", "ver": "v001", "text": "長いので分けて", "status": "open",
                                           "created_at": 1, "posted_latest": "v001"})
        self.sentence("前半。", **{"from": "s0003"})
        self.store("comments/c0004.json", {"sid": "s0003", "ver": "v001", "text": "外したあとの指摘", "status": "open",
                                           "created_at": 2 ** 62, "posted_latest": "v001"})
        by_text = {c["text"]: c for c in map(json.loads, self.cli("comments", self.root).stdout.splitlines())}
        self.assertEqual((by_text["長いので分けて"]["status"], by_text["長いので分けて"]["addressed_by"]), ("resolved", "retired"))
        self.assertEqual(by_text["外したあとの指摘"]["status"], "open")
        self.assertIsInstance(self.load("order.json")["retired"][-1]["at"], int)
        # examples は外した文へのコメントで止まらない（retired をバージョンとして読まない）
        out = self.cli("examples", self.root).stdout   # 一覧は setUp の init が足している
        self.assertIn("（文を外した）", out)

    def test_doc_comments_resolve_only_when_their_item_changes(self):
        """要件定義書の項目へのコメントは、新しいバージョンでその項目が変わったときだけ対応済みになる（ADR-0005）。"""
        two = "## 1. 言いたいこと\n言いたいこと\n\n## 2. 読み手\n読み手\n"
        self.cli("req", self.root, input=two)
        self.store("comments/c0001.json", {"doc": "requirements", "ver": "r002", "item": "1", "text": "主張が弱い", "status": "open"})
        self.store("comments/c0002.json", {"doc": "requirements", "ver": "r002", "item": "2", "text": "読み手が狭い", "status": "open"})
        self.store("comments/c0003.json", {"doc": "requirements", "ver": "r002", "item": "9", "text": "無い項目", "status": "open"})
        self.cli("req", self.root, input=two.replace("言いたいこと\n言いたいこと", "言いたいこと\nもっと強い主張"))
        by_text = {c["text"]: c for c in map(json.loads, self.cli("comments", self.root).stdout.splitlines())}
        self.assertEqual((by_text["主張が弱い"]["status"], by_text["主張が弱い"]["addressed_by"]), ("resolved", "r003"))
        self.assertEqual(by_text["読み手が狭い"]["status"], "open")   # 2番は直していないので開いたまま
        self.assertIn("読み手", by_text["読み手が狭い"]["current_text"])
        self.assertEqual(by_text["無い項目"]["note"], "行き先の無いコメント")
        self.assertIn("r002 の 9: 行き先の無いコメント", self.cli("check", self.root, code=1).stdout)
        # 設計書の段落も同じ読み方をする
        self.cli("design", self.root, input=DESIGN.replace("r001", "r003"))
        self.store("comments/c0004.json", {"doc": "design", "ver": "d001", "item": "p2", "text": "順番が逆", "status": "open"})
        by_text = {c["text"]: c for c in map(json.loads, self.cli("comments", self.root).stdout.splitlines())}
        self.assertEqual((by_text["順番が逆"]["status"], by_text["順番が逆"]["note"]), ("open", None))

    def test_check_missing_memo_and_orphan_comment(self):
        """メモを失った AI のバージョンと、行き先の無いコメントを検出する。"""
        self.sentence("本文。")
        (self.root / "sentences/s0001/v001-memo.json").unlink()
        self.store("comments/one.json", {"sid": "s9999", "ver": "v001", "text": "不明"})
        result = self.cli("check", self.root, code=1)
        self.assertIn("AI のバージョンにメモがありません", result.stdout)
        self.assertIn("行き先の無いコメント", result.stdout)

    def test_readers_ignore_temporary_files(self):
        """書きかけのコメントやバージョンを、確定した記録と取り違えない。"""
        self.sentence("本文。")
        for relative in ("comments/.tmp-comment.json", "sentences/s0001/.tmp-v002.json",
                         "requirements/.tmp-r002.md", "reviews/.tmp-rv0001.json"):
            (self.root / relative).write_text("{", encoding="utf-8")
        self.assertEqual(self.cli("comments", self.root).stdout, "")
        self.cli("check", self.root)
        self.assertEqual(json.loads(self.cli("show", self.root).stdout)["ver"], "v001")

    def test_check_missing_requirements_bad_tags_and_order(self):
        """要件・閉じた語彙・並びの不整合も検査する。"""
        for text in ("要件を失う文。", "文機能が壊れる文。", "並びから落ちる文。"):
            self.sentence(text)
        (self.root / "requirements/r001.md").unlink()
        sentence = self.load("sentences/s0002/v001.json")
        sentence["tags"]["relation"] = "不正"
        self.store("sentences/s0002/v001.json", sentence)
        order = self.load("order.json")
        order["order"] = ["s0001", "s0002", "s9999"]
        self.store("order.json", order)
        result = self.cli("check", self.root, code=1)
        for message in ("文機能が指す要件のバージョンがありません", "語彙の外", "order にあるのに", "order にも retired にも"):
            self.assertIn(message, result.stdout)
        self.assertIn("s0002 v001: 文機能が指す要件のバージョンがありません", result.stdout)

    def test_clock_skew_warns_without_failing(self):
        """時計が戻った場合は破損扱いにせず、ずれを知らせる。"""
        self.sentence("本文。")
        sentence = self.load("sentences/s0001/v001.json")
        memo = self.load("sentences/s0001/v001-memo.json")
        memo["memo_at"] = sentence["memo_at"] = sentence["written_at"] + 1
        self.store("sentences/s0001/v001.json", sentence)
        self.store("sentences/s0001/v001-memo.json", memo)
        self.assertIn("時計のずれかもしれない", self.cli("check", self.root).stdout)

    def test_req_refuses_broken_headings(self):
        """一文から項目を切り出せない要件定義書は受け取らない（ADR-0003）。"""
        for text in ("見出しの無い要件\n", "## 依頼\n番号が無い\n", "## 1. 依頼\n\n## 3. 範囲\n番号が飛ぶ\n",
                     "## 1. 言いたいこと\n\n## 段落の設計\n要件に設計が混ざる\n"):
            self.cli("req", self.root, input=text, code=2)
        self.assertEqual([path.name for path in (self.root / "requirements").iterdir()], ["r001.md"])

    def test_design_versions_and_heading_checks(self):
        """設計書は要件定義書のバージョンを頭に持ち、段落の見出しを検査して積む。"""
        self.assertEqual(self.cli("design", self.root, input=DESIGN).stdout.strip(), "d001")
        for text in ("## p1 頭の行が無い\n", "要件定義書: r009\n\n## p1 無い要件を指す\n",
                     "要件定義書: r001\n\n## 1. 段落でない見出し\n", "要件定義書: r001\n\n## p2 p1 から始まらない\n"):
            self.cli("design", self.root, input=text, code=2)
        self.assertEqual(self.cli("design", self.root, input=DESIGN).stdout.strip(), "d002")
        self.assertEqual((self.root / "design/d001.md").read_text(encoding="utf-8"), DESIGN)

    def test_design_adds_folder_to_old_record(self):
        """設計書より前に作った記録にも、design で設計書を足せる。"""
        (self.root / "design").rmdir()
        self.assertEqual(self.cli("design", self.root, input=DESIGN).stdout.strip(), "d001")

    def test_write_records_paragraph_when_design_exists(self):
        """設計書のある記録では、文が属する段落と照らした設計書のバージョンを記録する。"""
        self.cli("design", self.root, input=DESIGN)
        result = self.cli("memo", self.root, "--text", "段落を指す")
        sid, ver = result.stdout.split()
        base = ["write", self.root, "--sid", sid, "--ver", ver, "--text", "本文。", "--tags", json.dumps(self.tags())]
        self.cli(*base, code=2)
        self.cli(*base, "--para", "p3", code=2)
        self.cli(*base, "--para", "p2", "--design", "d009", code=2)
        self.cli(*base, "--para", "p2")
        sentence = self.load(f"sentences/{sid}/{ver}.json")
        self.assertEqual((sentence["design"], sentence["para"]), ("d001", "p2"))
        self.assertEqual(json.loads(self.cli("show", self.root).stdout)["para"], "p2")
        self.cli("check", self.root)

    def test_write_without_design_keeps_paragraph_empty(self):
        """設計書の無い記録では段落を付けさせず、null で記録する。"""
        result = self.cli("memo", self.root, "--text", "設計書なし")
        sid, ver = result.stdout.split()
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--text", "本文。",
                 "--tags", json.dumps(self.tags()), "--para", "p1", code=2)
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--text", "本文。", "--tags", json.dumps(self.tags()))
        self.assertIsNone(self.load(f"sentences/{sid}/{ver}.json")["para"])

    def test_check_warns_on_old_records_and_stale_design(self):
        """古い記録の抜けと古い要件に基づく設計書は警告だけにし、壊れた段落の指し先は誤りにする。"""
        self.sentence("最初の段落。", tags=self.tags(relation="段落の始まり"))
        self.sentence("次の段落。", tags=self.tags(relation="段落の始まり"))
        result = self.cli("check", self.root)
        self.assertIn("設計書がありません", result.stderr)
        self.assertEqual(result.stdout, "")
        self.cli("design", self.root, input=DESIGN)
        self.cli("req", self.root, input="## 1. 言いたいこと\n改めた要件\n")
        result = self.cli("check", self.root)
        self.assertIn("段落の番号の無い文が 2 文", result.stderr)
        self.assertIn("r001 に基づいています", result.stderr)
        sentence = self.load("sentences/s0001/v001.json")
        sentence["design"], sentence["para"] = "d001", "p9"
        self.store("sentences/s0001/v001.json", sentence)
        self.assertIn("設計書 d001 に段落 p9 がありません", self.cli("check", self.root, code=1).stdout)

    def test_init_is_idempotent_outside_git(self):
        """再初期化してもバージョンと並びを残し、git の外の ignore に触れない。"""
        self.sentence("残す本文。")
        previous = (self.root / "order.json").read_bytes()
        ignore = self.directory / ".gitignore"
        ignore.write_text("残す\n", encoding="utf-8")
        self.cli("init", self.document)
        self.cli("init", self.document)
        self.assertEqual((self.root / "order.json").read_bytes(), previous)
        self.assertEqual(ignore.read_text(encoding="utf-8"), "残す\n")
        self.assertEqual(self.load("sentences/s0001/v001.json")["text"], "残す本文。")

    def test_init_adds_gitignore_once_at_repository_root(self):
        """子フォルダから初期化しても、根の ignore にだけ1行足す。"""
        subprocess.run(["git", "init", "-q", str(self.directory)], check=True, env=self.env)
        ignore = self.directory / ".gitignore"
        ignore.write_text("existing", encoding="utf-8")
        child = self.directory / "sub"
        child.mkdir()
        document = child / "draft.md"
        self.cli("init", document)
        self.cli("init", document)
        self.assertEqual(ignore.read_text(encoding="utf-8"), "existing\n*.tsuzuri/\n")
        self.assertFalse((child / ".gitignore").exists())
        ignored = subprocess.run(["git", "-C", str(self.directory), "check-ignore", str(document) + ".tsuzuri/order.json"],
                                 capture_output=True, text=True, env=self.env)
        self.assertEqual(ignored.returncode, 0, ignored.stderr)

    def test_invalid_placement_leaves_no_new_memo(self):
        """位置の指定を誤っても、未使用のバージョンを作らない。"""
        self.sentence("本文。")
        for arguments in (["--after", "s9999"], ["--from", "s9999"],
                          ["--after", "s0001", "--from", "s0001"], ["--from", "s0001,s0001"]):
            with self.subTest(arguments=arguments):
                self.cli("memo", self.root, "--text", "予定", *arguments, code=2)
        self.assertFalse((self.root / "sentences/s0002").exists())

    def test_empty_export_and_version_number_overflow(self):
        """空の本文を書き出し、桁が増えても番号順にバージョンを選ぶ。"""
        self.cli("export", self.root)
        self.assertEqual((self.root / "text.md").read_bytes(), b"")
        self.cli("write", self.root, "--human", "--sid", "s9999", "--ver", "v999", "--text", "前。",
                 "--tags", json.dumps(self.tags()))
        self.cli("write", self.root, "--human", "--sid", "s9999", "--text", "次。",
                 "--tags", json.dumps(self.tags()))
        self.assertEqual(json.loads(self.cli("show", self.root).stdout)["ver"], "v1000")
        self.assertEqual(self.cli("memo", self.root, "--text", "新しい文").stdout.strip(), "s10000 v001")

    def test_block_versions_memos_and_immutability(self):
        """旧記録にも保存先を足し、ブロックのメモと確定版を上書きせず積む。"""
        self.assertTrue((self.root / "blocks").is_dir())
        (self.root / "blocks").rmdir()
        self.sentence("本文。")
        sid, ver = self.block({"kind": "heading", "level": 2}, "見出し", after="s0001")
        self.assertEqual((sid, ver), ("b0001", "v001"))
        self.assertEqual(self.load("order.json")["order"], ["s0001", "b0001"])
        paths = [self.root / f"blocks/{sid}/{ver}{suffix}.json" for suffix in ("", "-memo")]
        previous = [path.read_bytes() for path in paths]
        base = ["write", self.root, "--sid", sid, "--ver", ver, "--block", '{"kind":"image"}',
                "--text", "上書き", "--tags", '{"place":"要件"}']
        self.cli(*base, code=2)
        self.assertEqual([path.read_bytes() for path in paths], previous)
        self.assertEqual(self.cli("memo", self.root, "--sid", sid, "--text", "改める").stdout.strip(), "b0001 v002")
        pending = (self.root / "blocks/b0001/v002-memo.json").read_bytes()
        self.cli("memo", self.root, "--sid", sid, "--text", "飛ばす", code=2)
        self.cli("write", self.root, "--human", "--sid", sid, "--ver", "v003", "--block", '{"kind":"image"}',
                 "--text", "飛ばす", "--tags", '{"place":"要件"}', code=2)
        self.assertEqual((self.root / "blocks/b0001/v002-memo.json").read_bytes(), pending)
        self.cli("write", self.root, "--sid", sid, "--ver", "v002", "--block", '{"kind":"heading","level":3}',
                 "--text", "改めた見出し", "--tags", '{"place":"要件"}', "--deviation", "段を改めた")
        latest = self.load("blocks/b0001/v002.json")
        self.assertEqual((latest["requirements"], latest["deviation"], latest["source"]), ("r001", "段を改めた", "ai"))
        self.assertEqual(latest["memo_at"], self.load("blocks/b0001/v002-memo.json")["memo_at"])
        self.assertEqual([path.read_bytes() for path in paths], previous)
        self.cli("check", self.root)

    def test_block_write_requires_spec_and_memo_and_human_allocates(self):
        """ブロックの必須指定を検査し、人の記録では ID とメモを省ける。"""
        base = ["write", self.root, "--sid", "b0001", "--ver", "v001", "--text", "画像", "--tags", '{"place":"要件"}']
        self.cli(*base, code=2)
        self.assertIn("メモ", self.cli(*base, "--block", '{"kind":"image"}', code=2).stderr)
        self.cli("write", self.root, "--human", "--sid", "s0001", "--text", "文。", "--tags", json.dumps(self.tags()),
                 "--block", '{"kind":"image"}', code=2)
        (self.root / "blocks").rmdir()
        for number in (1, 2):
            result = self.cli("write", self.root, "--human", "--block", '{"kind":"image"}',
                              "--text", "![画像](a.png)", "--tags", '{"place":"要件"}')
            self.assertEqual(result.stdout.strip(), f"b{number:04d} v001")
        self.assertIsNone(self.load("blocks/b0001/v001.json")["memo_at"])
        self.cli("check", self.root)

    def test_blocks_reject_sentence_origins(self):
        """ブロックを分割・統合の元や先にできず、並べる位置には使える。"""
        self.sentence("元。")
        self.block({"kind": "image"}, "画像")
        for arguments in (["--block", "--from", "s0001"], ["--block", "--from", ""], ["--sid", "b0001", "--from", "s0001"],
                          ["--from", "b0001"], ["--sid", "s0001", "--block"]):
            self.cli("memo", self.root, "--text", "分ける", *arguments, code=2)
        self.assertFalse((self.root / "blocks/b0002").exists())
        self.sentence("直後。", after="b0001")
        self.block({"kind": "image"}, "次の画像", after="b0001")
        self.assertEqual(self.load("order.json")["order"], ["s0001", "b0001", "b0002", "s0002"])
        order = self.load("order.json")
        order["retired"] = [{"sid": "b0001", "into": ["s0001"]}]
        self.store("order.json", order)
        self.cli("check", self.root, code=2)

    def test_invalid_block_specs_and_text_do_not_write(self):
        """種類・必須属性・型と、入れ物と内容の本文条件を保存前に検査する。"""
        bad = [({}, "内容"), ([], "内容"), ({"kind": []}, "内容"), ({"kind": "unknown"}, "内容"),
               ({"kind": "heading"}, "内容"), ({"kind": "heading", "level": True}, "内容"),
               ({"kind": "heading", "level": 2.0}, "内容"), ({"kind": "heading", "level": 0}, "内容"),
               ({"kind": "heading", "level": 5}, "内容"), ({"kind": "code"}, "内容"),
               ({"kind": "code", "lang": 1}, "内容"), ({"kind": "note"}, ""),
               ({"kind": "note", "type": "bad"}, ""), ({"kind": "list"}, ""),
               ({"kind": "list", "ordered": 1}, "")]
        bad += [(spec, " ") for spec in ({"kind": "heading", "level": 2}, {"kind": "code", "lang": ""},
                                          {"kind": "image"}, {"kind": "table"})]
        bad += [(spec, "内容") for spec in ({"kind": "note", "type": "info"}, {"kind": "list", "ordered": False},
                                            {"kind": "quote"})]
        for spec, text in bad:
            with self.subTest(spec=spec, text=text):
                self.cli("write", self.root, "--human", "--block", json.dumps(spec), "--text", text,
                         "--tags", '{"place":"要件"}', code=2)
        self.assertEqual(list((self.root / "blocks").iterdir()), [])
        for spec in ({"kind": "heading", "level": 1}, {"kind": "heading", "level": 4}, {"kind": "code", "lang": ""}, {"kind": "table"}):
            self.block(spec, "内容")
        for note_type in ("info", "warn", "alert"):
            self.block({"kind": "note", "type": note_type})
        self.cli("check", self.root)

    def test_invalid_block_tags_do_not_write(self):
        """対応要件を必須にし、空の配列や null でも文機能のキーを拒む。"""
        bad = [[], {}, {"place": " "}, {"place": 1}]
        bad += [{"place": "要件", field: value} for field, value in
                (("relation", None), ("importance", "核"), ("role", []), ("technique", []))]
        for tags in bad:
            with self.subTest(tags=tags):
                self.cli("write", self.root, "--human", "--block", '{"kind":"image"}',
                         "--text", "画像", "--tags", json.dumps(tags), code=2)
        self.assertEqual(list((self.root / "blocks").iterdir()), [])

    def test_sentence_container_validation(self):
        """最新の確定ブロックが入れ物のときだけ文の所属先にできる。"""
        self.block({"kind": "heading", "level": 2}, "見出し")
        self.block({"kind": "note", "type": "info"})
        self.cli("memo", self.root, "--block", "--text", "未確定の箱")
        base = ["write", self.root, "--human", "--text", "文。", "--tags", json.dumps(self.tags())]
        for bid in ("s0001", "b0001", "b0003", "b9999", "../b0002"):
            self.cli(*base, "--in", bid, code=2)
        self.cli(*base, "--in", "b0002")
        self.assertEqual(self.load("sentences/s0001/v001.json")["in"], "b0002")
        self.cli("check", self.root)
        self.cli("write", self.root, "--human", "--block", '{"kind":"quote"}', "--text", "",
                 "--tags", '{"place":"要件"}', "--in", "b0002", code=2)
        self.block({"kind": "image"}, "箱を画像に変更", sid="b0002")
        self.cli(*base, "--in", "b0002", code=2)
        self.assertIn("入れ物", self.cli("check", self.root, code=1).stdout)

    def test_check_container_contiguity_and_export_preserves_previous_file(self):
        """箱から離れた文と存在しない箱を検出し、書き出し済みの本文を壊さない。"""
        self.block({"kind": "quote"})
        for text in ("一。", "二。"):
            self.cli("write", self.root, "--human", "--text", text, "--tags", json.dumps(self.tags()), "--in", "b0001")
        self.sentence("外。")
        self.cli("export", self.root)
        previous = (self.root / "text.md").read_bytes()
        order = self.load("order.json")
        order["order"] = ["b0001", "s0001", "s0003", "s0002"]
        self.store("order.json", order)
        self.assertIn("s0002: 入れ物 b0001 の直後に続いていません", self.cli("check", self.root, code=1).stdout)
        self.cli("export", self.root, code=2)
        self.assertEqual((self.root / "text.md").read_bytes(), previous)
        order["order"].remove("s0002")
        self.store("order.json", order)
        self.assertIn("s0002: 入れ物 b0001 の直後に続いていません", self.cli("check", self.root, code=1).stdout)
        sentence = self.load("sentences/s0001/v001.json")
        sentence["in"] = "b9999"
        self.store("sentences/s0001/v001.json", sentence)
        self.assertIn("s0001: 入れ物の指し先が不正", self.cli("check", self.root, code=1).stdout)

    def test_export_article_with_blocks_and_meta(self):
        """付帯情報・内容ブロック・各入れ物・通常段落を記事の形で書き出す。"""
        old_meta = "title: 最初\n"
        self.assertEqual(self.cli("meta", self.root, input=old_meta).stdout.strip(), "m001")
        source = self.directory / "meta.md"
        source.write_text("title: 記事\ntags: [Python]", encoding="utf-8")
        self.assertEqual(self.cli("meta", self.root, "--file", source).stdout.strip(), "m002")
        self.assertEqual((self.root / "meta/m001.md").read_text(encoding="utf-8"), old_meta)
        self.block({"kind": "heading", "level": 2}, "見出し")
        self.sentence("一。")
        self.sentence("二。")
        self.block({"kind": "code", "lang": "python"}, "print(1)")
        self.block({"kind": "image"}, "![図](a.png)")
        self.block({"kind": "table"}, "| A |\n|---|\n| B |")
        for spec in ({"kind": "note", "type": "info"}, {"kind": "list", "ordered": False},
                     {"kind": "list", "ordered": True}, {"kind": "quote"}):
            bid, _ = self.block(spec)
            for text in ("項目一。", "項目二。"):
                self.cli("write", self.root, "--human", "--text", text, "--tags", json.dumps(self.tags()), "--in", bid)
        self.sentence("箱の後。")
        self.cli("export", self.root, "--flavor", "qiita")
        self.assertEqual((self.root / "text.md").read_text(encoding="utf-8"),
                         "---\ntitle: 記事\ntags: [Python]\n---\n\n## 見出し\n\n一。\n二。\n\n"
                         "```python\nprint(1)\n```\n\n![図](a.png)\n\n| A |\n|---|\n| B |\n\n"
                         ":::note info\n項目一。\n項目二。\n:::\n\n- 項目一。\n- 項目二。\n\n"
                         "1. 項目一。\n2. 項目二。\n\n> 項目一。\n> 項目二。\n\n箱の後。\n")
        self.cli("check", self.root)

    def test_list_item_continues_with_cont(self):
        """人の文の箇条書きは、--cont の文を前の文と同じ項目に続け、外では指定を拒む。"""
        bid, _ = self.block({"kind": "list", "ordered": False})
        human = lambda text, *extra: self.cli("write", self.root, "--human", "--text", text,
                                              "--tags", json.dumps(self.tags()), "--in", bid, *extra)
        human("条件があること。")
        human("通常は起きません。", "--cont")
        human("Next item.")
        human("Two words.", "--cont")
        self.cli("export", self.root)
        self.assertIn("- 条件があること。通常は起きません。\n- Next item. Two words.\n",
                      (self.root / "text.md").read_text(encoding="utf-8"))
        self.assertTrue(self.load("sentences/s0002/v001.json")["cont"])
        self.assertNotIn("cont", self.load("sentences/s0001/v001.json"))
        self.cli("check", self.root)
        # 箇条書きの外と、注記の箱の中では指定できない
        self.cli("write", self.root, "--human", "--text", "外。", "--tags", json.dumps(self.tags()), "--cont", code=2)
        note, _ = self.block({"kind": "note", "type": "info"})
        self.cli("write", self.root, "--human", "--text", "箱。", "--tags", json.dumps(self.tags()), "--in", note, "--cont", code=2)

    def test_export_writes_note_boxes_in_each_flavor(self):
        """注記の箱は意味で記録し、書き出しで媒体の方言に変える。既定は GitHub の Markdown。"""
        for spec in ({"kind": "note", "type": "info"}, {"kind": "note", "type": "warn"}):
            bid, _ = self.block(spec)
            self.cli("write", self.root, "--human", "--text", "中身。", "--tags", json.dumps(self.tags()), "--in", bid)
        expected = {
            None: "> [!NOTE]\n> 中身。\n\n> [!WARNING]\n> 中身。\n",
            "qiita": ":::note info\n中身。\n:::\n\n:::note warn\n中身。\n:::\n",
            "zenn": ":::message\n中身。\n:::\n\n:::message alert\n中身。\n:::\n",
        }
        for flavor, text in expected.items():
            with self.subTest(flavor=flavor):
                self.cli("export", self.root, *(["--flavor", flavor] if flavor else []))
                self.assertEqual((self.root / "text.md").read_text(encoding="utf-8"), text)
        self.cli("export", self.root, "--flavor", "note", code=2)

    def test_move_reorders_without_new_versions_and_refuses_containers(self):
        """move は並びだけを変え、文のバージョンを増やさない。入れ物のブロックと、無い文は断る。"""
        for text in ("一。", "二。", "三。"):
            self.sentence(text)
        self.cli("move", self.root, "--sid", "s0003", "--after", "s0001")
        self.assertEqual(self.load("order.json")["order"], ["s0001", "s0003", "s0002"])
        self.cli("move", self.root, "--sid", "s0002", "--after", "start")
        self.assertEqual(self.load("order.json")["order"], ["s0002", "s0001", "s0003"])
        self.cli("move", self.root, "--sid", "s0002", "--after", "s0003")
        self.assertEqual(len(list((self.root / "sentences/s0003").glob("v*.json"))) - len(list((self.root / "sentences/s0003").glob("*-memo.json"))), 1)
        bid, _ = self.block({"kind": "quote"})
        self.cli("write", self.root, "--human", "--text", "中。", "--tags", json.dumps(self.tags()), "--in", bid)
        self.cli("move", self.root, "--sid", bid, "--after", "s0001", code=2)
        self.cli("move", self.root, "--sid", "s0001", "--after", "s0001", code=2)
        self.cli("move", self.root, "--sid", "s0009", "--after", "s0001", code=2)
        self.cli("check", self.root)

    def test_load_lists_new_word_used_as_topic(self):
        """初めて出る語を「は」の主題にした文を挙げ、既に出た語と一般の語は挙げない。"""
        self.sentence("要件定義書は、書く前に決める文書です。")
        self.sentence("設計書という文書があります。")
        self.sentence("設計書は段落の並びを決めます。")
        self.sentence("この場合は、要件定義書から直します。")
        self.sentence("この文章は手元で読めます。")
        section = self.cli("load", self.root).stdout.split("## 初めて出る語の主題")[1].split("##")[0]
        self.assertIn("s0001", section)
        self.assertNotIn("s0003", section)
        self.assertNotIn("s0004", section)
        self.assertNotIn("s0005", section)

    def test_drift_lists_changed_negation_and_numbers(self):
        """1つ前のバージョンと比べ、否定と数値が変わった文を挙げる。言い回しだけの直しは挙げない。"""
        self.sentence("締め切りは3日です。")
        self.sentence("確認してください。")
        self.cli("memo", self.root, "--sid", "s0001", "--text", "狙い")
        self.cli("write", self.root, "--sid", "s0001", "--ver", "v002", "--text", "締め切りは5日ではありません。", "--tags", json.dumps(self.tags()))
        self.cli("memo", self.root, "--sid", "s0002", "--text", "狙い")
        self.cli("write", self.root, "--sid", "s0002", "--ver", "v002", "--text", "確かめてください。", "--tags", json.dumps(self.tags()))
        out = self.cli("drift", self.root).stdout
        self.assertIn("s0001 v001→v002 否定", out)
        self.assertIn("s0001 v001→v002 数値", out)
        self.assertNotIn("s0002", out)

    def test_footnote_reference_inside_inline_code_is_not_a_call(self):
        """インラインコードの中の [^ラベル] は脚注の呼び出しとして数えない。"""
        self.sentence("脚注は本文に `[^ラベル]` を書いて呼ぶ。")
        out = self.cli("check", self.root).stdout
        self.assertNotIn("脚注がありません", out)

    def test_footnotes_keep_the_paragraph_and_export_at_the_end(self):
        """脚注は本文の段落を区切らず、書き出しでは本文の末尾にまとめて出る。"""
        self.sentence("一[^a]。")
        bid, _ = self.block({"kind": "footnote", "label": "a"})
        for text in ("注の一。", "注の二。"):
            self.cli("write", self.root, "--human", "--text", text, "--tags", json.dumps(self.tags()), "--in", bid)
        self.sentence("二。")
        self.block({"kind": "heading", "level": 2}, "次")
        self.sentence("三[^b]。")
        self.block({"kind": "footnote", "label": "b"})
        self.cli("write", self.root, "--human", "--text", "注の三。", "--tags", json.dumps(self.tags()), "--in", "b0003")
        self.cli("check", self.root)
        self.cli("export", self.root)
        self.assertEqual((self.root / "text.md").read_text(encoding="utf-8"),
                         "一[^a]。\n二。\n\n## 次\n\n三[^b]。\n\n[^a]: 注の一。注の二。\n\n[^b]: 注の三。\n")
        starts = tsuzuri._paragraph_starts(self.root, self.load("order.json"))
        self.assertFalse(starts["s0004"])

    def test_records_without_footnote_blocks_only_warn_about_references(self):
        """脚注のブロックが無い前の記録では、呼び出しの不一致を誤りにせず警告に留める。"""
        self.sentence("一[^old]。")
        self.sentence("[^old]: 文として書いた脚注。")
        result = self.cli("check", self.root)
        self.assertIn("警告: s0001: [^old] を呼んでいますが", result.stderr)
        self.cli("export", self.root)

    def test_check_footnote_references_match_labels(self):
        """呼ばれない脚注・脚注の無い呼び出し・同じラベル・呼ぶ文より前の脚注を検出する。"""
        self.sentence("一[^a]。")
        self.block({"kind": "footnote", "label": "a"})
        self.cli("write", self.root, "--human", "--text", "注。", "--tags", json.dumps(self.tags()), "--in", "b0001")
        self.sentence("二[^missing]。")
        self.block({"kind": "footnote", "label": "a"})
        self.block({"kind": "footnote", "label": "unused"})
        output = self.cli("check", self.root, code=1).stdout
        self.assertIn("[^missing] を呼んでいますが、その脚注がありません", output)
        self.assertIn("脚注のラベル a が重複しています", output)
        self.assertIn("b0003: 脚注 unused はどの文からも呼ばれていません", output)
        self.cli("export", self.root, code=2)
        order = self.load("order.json")
        order["order"] = ["b0001", "s0002", "s0001"]
        self.store("order.json", order)
        self.assertIn("b0001: 脚注 a が呼ぶ文より前にあります", self.cli("check", self.root, code=1).stdout)
        self.cli("write", self.root, "--human", "--block", '{"kind":"footnote","label":"a b"}', "--text", "",
                 "--tags", '{"place":"要件"}', code=2)

    def test_paragraphs_use_design_and_fall_back_for_legacy_sentences(self):
        """設計があれば段落番号を使い、番号の無い旧文は接続の札を使う。"""
        self.cli("design", self.root, input=DESIGN)
        for para, text, relation in (("p1", "一。", "順接"), ("p1", "二。", "段落の始まり"),
                                     ("p2", "三。", "順接"), ("p2", "四。", "段落の始まり")):
            self.cli("write", self.root, "--human", "--text", text, "--para", para,
                     "--tags", json.dumps(self.tags(relation=relation)))
        sentence = self.load("sentences/s0004/v001.json")
        sentence.pop("para")
        sentence.pop("design")
        self.store("sentences/s0004/v001.json", sentence)
        self.cli("export", self.root)
        self.assertEqual((self.root / "text.md").read_text(encoding="utf-8"), "一。\n二。\n\n三。\n\n四。\n")
        self.assertEqual(list(tsuzuri._paragraph_starts(self.root, self.load("order.json")).values()),
                         [True, False, True, True])

    def test_show_includes_block_spec_and_latest_memo(self):
        """文とブロックを並び順で出し、最新版の意図と文の所属先を読める。"""
        self.block({"kind": "quote"})
        self.cli("write", self.root, "--human", "--text", "人の文。", "--tags", json.dumps(self.tags()), "--in", "b0001")
        shown = [json.loads(line) for line in self.cli("show", self.root).stdout.splitlines()]
        self.assertEqual(set(shown[0]), {"sid", "ver", "block", "para", "text", "tags", "memo"})
        self.assertEqual((shown[0]["block"], shown[0]["memo"]), ({"kind": "quote"}, "置く狙い"))
        self.assertEqual((shown[1]["in"], shown[1]["memo"]), ("b0001", None))
        self.assertEqual(list(tsuzuri._paragraph_starts(self.root, self.load("order.json")).values()), [False, True])
        for text, bid in (("同じ箱。", "b0001"), ("外。", None), ("箱へ戻る。", "b0001")):
            arguments = ["--in", bid] if bid else []
            self.cli("write", self.root, "--human", "--text", text, "--tags", json.dumps(self.tags()), *arguments)
        self.assertEqual(list(tsuzuri._paragraph_starts(self.root, self.load("order.json")).values()),
                         [False, True, False, False, True])

    def test_comments_can_point_to_blocks(self):
        """ブロックの旧版へのコメントも現在の本文を伴って読める。"""
        self.block({"kind": "heading", "level": 2}, "元の見出し")
        self.store("comments/c0001.json", {"sid": "b0001", "ver": "v001", "text": "段を変えて"})
        self.block({"kind": "heading", "level": 3}, "今の見出し", sid="b0001")
        comment = json.loads(self.cli("comments", self.root).stdout)
        self.assertEqual((comment["current_text"], comment["note"]), ("今の見出し", None))
        self.cli("check", self.root)

    def test_check_validates_block_versions_memos_and_design(self):
        """ブロックの破損を文と同じ規則で検出し、時計のずれだけは失敗させない。"""
        self.cli("design", self.root, input=DESIGN)
        self.cli("memo", self.root, "--block", "--text", "見出しの狙い")
        base = ["write", self.root, "--sid", "b0001", "--ver", "v001", "--block", '{"kind":"heading","level":2}',
                "--text", "見出し", "--tags", '{"place":"要件"}']
        self.cli(*base, code=2)
        self.cli(*base, "--para", "p1", "--requirements", "r999", code=2)
        self.cli(*base, "--para", "p1")
        path = "blocks/b0001/v001.json"
        original = self.load(path)
        for changes, message in (({"sid": "b0002"}, "ID がファイル名と一致"), ({"ver": "v002"}, "ID がファイル名と一致"),
                                 ({"block": {"kind": "heading", "level": 0}}, "block.level"),
                                 ({"tags": {"place": "要件", "role": []}}, "ブロックの文機能"),
                                 ({"requirements": "r999"}, "要件のバージョンがありません"),
                                 ({"memo_at": 0}, "メモの時刻が文の記録と一致"),
                                 ({"para": "p9"}, "段落 p9 がありません"),
                                 ({"design": "d999"}, "設計書のバージョンがありません")):
            with self.subTest(changes=changes):
                self.store(path, {**original, **changes})
                self.assertIn(message, self.cli("check", self.root, code=1).stdout)
        self.store(path, original)
        memo_path = "blocks/b0001/v001-memo.json"
        memo = self.load(memo_path)
        self.store(memo_path, {**memo, "sid": "b0002"})
        self.assertIn("メモの ID がファイル名と一致", self.cli("check", self.root, code=1).stdout)
        memo["memo_at"] = original["memo_at"] = original["written_at"] + 1
        self.store(path, original)
        self.store(memo_path, memo)
        self.assertIn("時計のずれかもしれない", self.cli("check", self.root).stdout)
        (self.root / memo_path).unlink()
        self.assertIn("AI のバージョンにメモがありません", self.cli("check", self.root, code=1).stdout)
        order = self.load("order.json")
        order["order"].append("b9999")
        self.store("order.json", order)
        self.assertIn("b9999: order にあるのに", self.cli("check", self.root, code=1).stdout)

    def test_atomic_write_fsyncs_before_replace_and_after(self):
        """一時ファイルの同期・置換・親フォルダの同期の順を守る。"""
        target = self.directory / "atomic.json"
        fsync = os.fsync
        replace = os.replace
        events = []

        def sync(descriptor):
            events.append("fsync")
            fsync(descriptor)

        def move(source, destination):
            self.assertEqual(source.parent, target.parent)
            self.assertTrue(source.name.startswith(".tmp-"))
            self.assertEqual(source.read_text(encoding="utf-8"), "確定する内容")
            events.append("replace")
            replace(source, destination)

        with patch.object(tsuzuri.os, "fsync", side_effect=sync), patch.object(tsuzuri.os, "replace", side_effect=move):
            tsuzuri._atomic_write(target, "確定する内容")
        self.assertEqual(events, ["fsync", "replace", "fsync"])
        self.assertEqual(list(self.directory.glob(".tmp-*")), [])

    def test_atomic_write_failure_preserves_old_file(self):
        """確定に失敗したら前のファイルを保ち、一時ファイルを片付ける。"""
        target = self.directory / "atomic.json"
        target.write_text("前の内容", encoding="utf-8")
        with patch.object(tsuzuri.os, "replace", side_effect=OSError("保存失敗")):
            with self.assertRaises(OSError):
                tsuzuri._atomic_write(target, "新しい内容")
        self.assertEqual(target.read_text(encoding="utf-8"), "前の内容")
        self.assertEqual(list(self.directory.glob(".tmp-*")), [])


    def test_container_retire_split_merge_and_empty_export(self):
        """C#1・A#4: 各入れ物の退役履歴が検査を妨げず、空になっても書き出せる。"""
        specs = ({"kind": "list", "ordered": False}, {"kind": "note", "type": "info"},
                 {"kind": "quote"}, {"kind": "footnote", "label": "removed"})
        for spec in specs:
            with self.subTest(kind=spec["kind"]):
                if spec["kind"] == "footnote":
                    self.sentence("呼び出し[^removed]。")
                bid, _ = self.block(spec)
                children = []
                for text in ("削る文。", "分ける文。"):
                    sid, _ = self.cli("write", self.root, "--human", "--text", text,
                                      "--tags", json.dumps(self.tags()), "--in", bid).stdout.split()
                    children.append(sid)
                original = (self.root / f"sentences/{children[0]}/v001.json").read_bytes()
                self.cli("retire", self.root, "--sid", children[0], "--text", "不要")
                self.cli("check", self.root)
                self.cli("export", self.root)
                split = []
                for text in ("前半。", "後半。"):
                    sid, ver = self.cli("memo", self.root, "--from", children[1], "--text", "分けた狙い").stdout.split()
                    self.cli("write", self.root, "--sid", sid, "--ver", ver, "--text", text,
                             "--tags", json.dumps(self.tags()), "--in", bid)
                    split.append(sid)
                    self.cli("check", self.root)
                    self.cli("export", self.root)
                sid, ver = self.cli("memo", self.root, "--from", ",".join(split), "--text", "一つの狙い").stdout.split()
                self.cli("write", self.root, "--sid", sid, "--ver", ver, "--text", "統合した文。",
                         "--tags", json.dumps(self.tags()), "--in", bid)
                self.cli("check", self.root)
                self.cli("export", self.root)
                self.assertIn("統合した文。", (self.root / "text.md").read_text(encoding="utf-8"))
                self.cli("retire", self.root, "--sid", sid, "--text", "全て不要")
                self.cli("check", self.root)
                self.cli("export", self.root)
                text = (self.root / "text.md").read_text(encoding="utf-8")
                self.assertNotIn("統合した文。", text)
                self.assertNotIn("[!NOTE]", text)
                if spec["kind"] == "footnote":
                    self.assertIn("[^removed]: ", text)
                self.assertEqual((self.root / f"sentences/{children[0]}/v001.json").read_bytes(), original)

    def test_windows_directory_sync_skips_open(self):
        """C#2: Windows のフォルダ同期は開かずに戻り、ファイル同期の処理は残る。"""
        with patch.object(tsuzuri.os, "name", "nt"), patch.object(tsuzuri.os, "open") as opened:
            tsuzuri._sync_directory(self.directory)
        opened.assert_not_called()
        target = self.directory / "windows-write.json"
        with patch.object(tsuzuri, "_sync_directory"), patch.object(tsuzuri.os, "fsync", wraps=os.fsync) as synced:
            tsuzuri._atomic_write(target, "内容")
        synced.assert_called_once()

    def test_windows_registry_lock_releases_after_failure(self):
        """Windows の一覧更新も固定ファイルの先頭をロックし、例外時にも解除する。"""
        path = self.directory / "windows-registry.json"
        msvcrt = SimpleNamespace(LK_LOCK=1, LK_UNLCK=0, locking=Mock())
        with patch.object(tsuzuri, "registry_path", return_value=path), patch.object(tsuzuri.os, "name", "nt"), \
                patch.dict(sys.modules, {"msvcrt": msvcrt}):
            with self.assertRaises(ValueError), tsuzuri._registry_lock():
                raise ValueError("更新失敗")
            with tsuzuri._registry_lock():
                pass
        self.assertEqual([(call.args[1], call.args[2]) for call in msvcrt.locking.call_args_list],
                         [(1, 1), (0, 1), (1, 1), (0, 1)])
        self.assertEqual(path.with_name(path.name + ".lock").read_bytes(), b"\0")

    def test_retry_write_recovers_order_without_changing_confirmed_version(self):
        """A#3: 並び保存の障害後、同じ write だけが履歴を上書きせず配置と移行先を復旧する。"""
        self.sentence("統合前の一。")
        self.sentence("統合前の二。")
        for options, block in (([], False), (["--after", "s0001"], True),
                               (["--from", "s0001,s0002"], False)):
            sid, ver = self.cli("memo", self.root, "--text", "新しい狙い", *options,
                                *(["--block"] if block else [])).stdout.split()
            args = ["write", str(self.root), "--sid", sid, "--ver", ver, "--text", "本文。",
                    "--tags", json.dumps({"place": "要件"} if block else self.tags())]
            if block:
                args += ["--block", '{"kind":"heading","level":2}']
            write_json = tsuzuri._write_json

            def fail_order(path, value, **kwargs):
                if path.name == "order.json":
                    raise OSError("並び保存失敗")
                return write_json(path, value, **kwargs)

            previous = (self.root / "order.json").read_bytes()
            with patch.object(tsuzuri, "_write_json", side_effect=fail_order):
                self.assertEqual(tsuzuri.main(args), 2)
            path = tsuzuri._sentence_path(self.root, sid, ver)
            confirmed = path.read_bytes()
            self.assertEqual((self.root / "order.json").read_bytes(), previous)
            changed = args.copy()
            changed[changed.index("--text") + 1] = "違う本文。"
            self.cli(*changed, code=2)
            self.assertEqual((self.root / "order.json").read_bytes(), previous)
            self.cli(*args)
            self.assertEqual(path.read_bytes(), confirmed)
            self.assertIn(sid, self.load("order.json")["order"])
            self.cli("check", self.root)
            self.cli("export", self.root)
        self.assertEqual(without_at(self.load("order.json")["retired"]),
                         [{"sid": "s0001", "into": [sid]}, {"sid": "s0002", "into": [sid]}])

    def test_examples_before_init_and_with_retired_comment(self):
        """C#5・A#13: 記録なしで空の一覧と他の記録の修正・削除例を読める。"""
        self.assertEqual(self.cli("examples").stdout, "")
        self.sentence("元の文。")
        self.store("comments/c0001.json", {"sid": "s0001", "ver": "v001", "text": "直して", "status": "open"})
        self.sentence("直した文。", sid="s0001")
        future = self.directory / "未作成.md.tsuzuri"
        example = json.loads(self.cli("examples", future).stdout)
        self.assertEqual((example["before"], example["after"]), ("元の文。", "直した文。"))
        self.cli("retire", self.root, "--sid", "s0001", "--text", "不要")
        # 新しいバージョンで先に対応したコメントは、あとで文を外しても、その直しを例として残す
        self.assertEqual(json.loads(self.cli("examples").stdout)["after"], "直した文。")
        # 直さずに外した文へのコメントは、外したことで対応した例になる
        self.sentence("別の文。")
        self.store("comments/c0002.json", {"sid": "s0002", "ver": "v001", "text": "要らない", "status": "open"})
        self.cli("retire", self.root, "--sid", "s0002", "--text", "不要")
        afters = [json.loads(line)["after"] for line in self.cli("examples").stdout.splitlines()]
        self.assertIn("（文を外した）", afters)
        self.assertFalse(future.exists())

    def test_examples_skip_received_and_broken_records(self):
        """人から受け取った記録の直しは手本に混ぜず、壊れた記録が1つあってもほかの記録の手本は出す。"""
        self.sentence("元の文。")
        self.store("comments/c0001.json", {"sid": "s0001", "ver": "v001", "text": "直して", "status": "open"})
        self.sentence("直した文。", sid="s0001")
        self.assertEqual(len(self.cli("examples").stdout.splitlines()), 1)
        packed = self.directory / "共有.tsz"
        self.cli("pack", self.root, "--out", packed)
        target = self.directory / "受け取り"
        target.mkdir()
        self.cli("unpack", packed, "--dir", target)
        broken = self.directory / "壊れ.md.tsuzuri"
        self.cli("init", self.directory / "壊れ.md")   # 一覧に足してから、入れ子の深すぎる JSON に壊す
        (broken / "order.json").chmod(0o644)
        (broken / "order.json").write_text("[" * 100000, encoding="utf-8")
        result = self.cli("examples")
        self.assertEqual(len(result.stdout.splitlines()), 1)
        self.assertIn("壊れ.md.tsuzuri", result.stderr)

    def test_retry_human_write_recovers_automatic_ids(self):
        """A#3: 人の文とブロックも、ID・バージョンを省いた同じ write で復旧できる。"""
        for extra in ([], ["--block", '{"kind":"heading","level":2}']):
            args = ["write", str(self.root), "--human", "--text", "自筆。", *extra,
                    "--tags", json.dumps({"place": "要件"} if extra else self.tags())]
            write_json = tsuzuri._write_json

            def fail_order(path, value, **kwargs):
                if path.name == "order.json":
                    raise OSError("並び保存失敗")
                return write_json(path, value, **kwargs)

            with patch.object(tsuzuri, "_write_json", side_effect=fail_order):
                self.assertEqual(tsuzuri.main(args), 2)
            sid = "b0001" if extra else "s0001"
            path = tsuzuri._sentence_path(self.root, sid, "v001")
            confirmed = path.read_bytes()
            self.assertEqual(self.cli(*args).stdout.strip(), f"{sid} v001")
            self.assertEqual(path.read_bytes(), confirmed)
            self.cli("check", self.root)

    def test_registry_concurrent_registration_and_removal(self):
        """A#10: 別プロセスによる登録と除外の読み取り・置換を同じロックで守る。"""
        worker = """
import importlib.util, sys, time
spec = importlib.util.spec_from_file_location('cli', sys.argv[1])
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
read = cli.read_registry
def delayed_read():
    paths = read()
    time.sleep(0.2)
    return paths
cli.read_registry = delayed_read
print('ready', flush=True)
getattr(cli, sys.argv[2])(sys.argv[3])
"""
        a, b, c = [str(self.directory / name) for name in ("a", "b", "c")]
        with patch.dict(os.environ, {"TSUZURI_REGISTRY": self.env["TSUZURI_REGISTRY"]}):
            for operations in ((("register_record", a), ("register_record", b)),
                               (("forget_record", a), ("register_record", c))):
                processes = []
                with tsuzuri._registry_lock():
                    for operation, path in operations:
                        process = subprocess.Popen([sys.executable, "-c", worker, str(SCRIPT), operation, path],
                                                   env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        processes.append(process)
                        self.addCleanup(lambda p=process: p.poll() is None and p.kill())
                        self.assertEqual(process.stdout.readline().strip(), "ready")
                for process in processes:
                    out, error = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 0, out + error)
            self.assertEqual(tsuzuri.read_registry(), [str(self.root), b, c])

    def test_comment_version_numbers_across_999_and_reopening(self):
        """A#14: 文・要件・設計とも999から1000への更新と再開を数値で判定する。"""
        self.sentence("旧文。")
        sentence = self.load("sentences/s0001/v001.json")
        self.store("sentences/s0001/v999.json", {**sentence, "ver": "v999", "source": "human"})
        self.store("comments/c0001.json", {"sid": "s0001", "ver": "v999", "status": "open", "text": "直して"})
        self.store("sentences/s0001/v1000.json", {**sentence, "ver": "v1000", "source": "human"})
        comment = json.loads(self.cli("comments", self.root).stdout)
        self.assertEqual((comment["status"], comment["addressed_by"]), ("resolved", "v1000"))
        self.store("comments/c0001.json", {**comment, "status": "open", "reopened_at_ver": "v1000"})
        self.assertEqual(json.loads(self.cli("comments", self.root).stdout)["status"], "open")
        for kind, prefix, item, template in (("requirements", "r", "1", "## 1. 依頼\n{}"),
                                              ("design", "d", "p1", "要件定義書: r001\n## p1 主張\n{}")):
            for ver, text in ((999, "前"), (1000, "後")):
                (self.root / kind / f"{prefix}{ver}.md").write_text(template.format(text), encoding="utf-8")
            comment = {"doc": kind, "ver": f"{prefix}999", "item": item, "text": "直して", "status": "open"}
            result = tsuzuri._doc_comment(self.root, comment)
            self.assertEqual(result["addressed_by"], f"{prefix}1000")
            self.assertEqual(tsuzuri._doc_comment(self.root, {**comment, "reopened_at_ver": f"{prefix}1000"})["status"], "open")

    def test_cold_footnotes_follow_body_and_preserve_design_paragraphs(self):
        """C#11: 脚注はラベルと文ID付きで末尾に分け、本文の段落は export とそろえる。"""
        self.cli("req", self.root, input="## 1. 依頼\n依頼\n## 2. 書く理由\n理由\n## 3. 公開する場所と読み手\n読者\n")
        self.cli("design", self.root, input=DESIGN.replace("r001", "r002"))
        for text, extra in (("本文[^a]。", []), ("", ["--block", '{"kind":"footnote","label":"a"}']),
                            ("脚注の文。", ["--in", "b0001"]), ("本文の続き。", [])):
            self.cli("write", self.root, "--human", "--para", "p1", "--text", text, *extra,
                     "--tags", json.dumps({"place": "要件"} if "--block" in extra else self.tags(relation="段落の始まり")))
        out = self.cli("cold", self.root).stdout
        self.assertIn("[s0001] 本文[^a]。\n[s0003] 本文の続き。\n\n[b0001] [^a]:\n[s0002] 脚注の文。", out)
        self.cli("export", self.root)
        self.assertEqual((self.root / "text.md").read_text(encoding="utf-8"), "本文[^a]。\n本文の続き。\n\n[^a]: 脚注の文。\n")

    def test_cold_marks_sentences_inside_containers(self):
        """箇条書きの中の文は印を付けて入れ物の下に並べ、入れ物を出た地の文は段落を区切る（中身の見えない箱と読まれないため）。"""
        self.cli("req", self.root, input="## 1. 依頼\n依頼\n## 2. 書く理由\n理由\n## 3. 公開する場所と読み手\n読者\n")
        for text, extra in (("前置き。", []), ("", ["--block", '{"kind":"list","ordered":true}']),
                            ("一つ目。", ["--in", "b0001"]), ("二つ目。", ["--in", "b0001"]), ("続き。", [])):
            self.cli("write", self.root, "--human", "--text", text, *extra,
                     "--tags", json.dumps({"place": "要件"} if "--block" in extra else self.tags(relation="添加")))
        out = self.cli("cold", self.root).stdout
        self.assertIn("[b0001] （list）中身は下の印の付いた行\n[s0002] 1. 一つ目。\n[s0003] 2. 二つ目。\n\n[s0004] 続き。", out)

    def test_tags_reject_extra_keys_in_write_and_check(self):
        """C#18: 文とブロックは打ち間違えたキーを保存前と検査時の両方で拒む。"""
        for block, tags in ((False, {**self.tags(), "技法": []}), (True, {"place": "要件", "plcae": "誤記"})):
            extra = ["--block", '{"kind":"heading","level":2}'] if block else []
            self.cli("write", self.root, "--human", "--text", "本文。", "--tags", json.dumps(tags), *extra, code=2)
            sid, _ = self.block({"kind": "heading", "level": 2}, "見出し") if block else self.sentence("本文。")
            path = f"{'blocks' if block else 'sentences'}/{sid}/v001.json"
            original = self.load(path)
            self.store(path, {**original, "tags": tags})
            self.assertIn("キー", self.cli("check", self.root, code=1).stdout)
            self.store(path, original)

    def test_extra_keys_left_only_in_old_version_are_a_warning(self):
        """古いバージョンだけに残った余分なキーは、新しいバージョンで直せるので check を止めない。"""
        sid, _ = self.sentence("本文。")
        path = f"sentences/{sid}/v001.json"
        original = self.load(path)
        self.store(path, {**original, "tags": {**original["tags"], "技法": []}})
        self.assertIn("キー", self.cli("check", self.root, code=1).stdout)
        ver = self.cli("memo", self.root, "--sid", sid, "--text", "同じ狙い").stdout.split()[1]
        self.cli("write", self.root, "--sid", sid, "--ver", ver, "--text", "本文。", "--tags", json.dumps(self.tags()))
        result = self.cli("check", self.root, code=0)
        self.assertIn("警告", result.stdout)

    def test_drift_since_compares_restored_text_to_selected_version(self):
        """C#13の4: 元へ戻した文は起点指定で消え、省略時の直前比較は変わらない。"""
        self.sentence("3日です。")
        self.sentence("5日です。", sid="s0001")
        self.sentence("3日です。", sid="s0001")
        self.assertIn("v002→v003 数値", self.cli("drift", self.root).stdout)
        self.assertEqual(self.cli("drift", self.root, "--since", "v001").stdout, "")
        self.assertIn("v002→v003 数値", self.cli("drift", self.root, "--since", "v002").stdout)
        self.assertEqual(self.cli("drift", self.root, "--since", "v999").stdout, "")
        self.cli("drift", self.root, "--since", "../v001", code=2)

    def test_posted_latest_comments_wait_for_a_new_sentence_version(self):
        """C#12: 旧文への新しいコメントは投稿時の最新を越えるまで開いたままで、旧形式は従来どおり。"""
        self.sentence("前。")
        self.sentence("今。", sid="s0001")
        base = {"sid": "s0001", "ver": "v001", "text": "見直して", "status": "open"}
        self.store("comments/c0001.json", {**base, "posted_latest": "v002"})
        self.store("comments/c0002.json", base)
        comments = [json.loads(line) for line in self.cli("comments", self.root).stdout.splitlines()]
        self.assertEqual([c["status"] for c in comments], ["open", "resolved"])
        self.sentence("直した文。", sid="s0001")
        comments = [json.loads(line) for line in self.cli("comments", self.root).stdout.splitlines()]
        self.assertEqual([c["status"] for c in comments], ["resolved", "resolved"])
        self.assertEqual(comments[0]["addressed_by"], "v003")
        self.assertEqual(self.load("comments/c0001.json")["status"], "open")
        self.store("comments/c0001.json", {**base, "posted_latest": "v003"})
        self.cli("retire", self.root, "--sid", "s0001", "--text", "不要")
        comments = [json.loads(line) for line in self.cli("comments", self.root).stdout.splitlines()]
        self.assertEqual([c["status"] for c in comments], ["open", "resolved"])

    def test_posted_latest_document_comments_compare_the_posting_version(self):
        """C#12: 要件と設計は投稿後に対象の項目が変わったときだけ対応済みになる。"""
        for kind, prefix, item, template in (("requirements", "r", "1", "## 1. 依頼\n{}\n## 2. 理由\n{}"),
                                              ("design", "d", "p1", "要件定義書: r001\n## p1 主張\n{}\n## p2 理由\n{}")):
            for number, text in ((1, "前"), (2, "投稿前の変更"), (3, "投稿前の変更"), (4, "投稿後の変更")):
                path = self.root / kind / f"{prefix}{number:03d}.md"
                path.write_text(template.format(text, number), encoding="utf-8")
                if number < 2:
                    continue
                comment = {"doc": kind, "ver": f"{prefix}001", "item": item, "text": "直して", "status": "open",
                           "posted_latest": f"{prefix}002"}
                self.assertEqual(tsuzuri._doc_comment(self.root, comment)["status"], "resolved" if number == 4 else "open")
                legacy = {k: v for k, v in comment.items() if k != "posted_latest"}
                self.assertEqual(tsuzuri._doc_comment(self.root, legacy)["status"], "resolved")


if __name__ == "__main__":
    unittest.main()
