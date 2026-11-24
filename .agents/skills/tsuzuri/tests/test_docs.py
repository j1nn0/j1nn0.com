"""配る文書（SKILL.md と references）に書いた例と項目名が、CLI とアプリに受け取られる形かを確かめる。

文書だけが古いまま残ると、例どおりに書いた AI の記録をアプリが読めない（Astra の厳格レビュー #12・
tag-vocabulary.md が8項目と段落の番号を place に書くよう案内していた）。
"""

import importlib.util
import json
from pathlib import Path
import re
import shlex
import tempfile
import unittest


SKILL_DIR = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tsuzuri", SKILL_DIR / "scripts" / "tsuzuri.py")
tsuzuri = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tsuzuri)

DOCS = [SKILL_DIR / "SKILL.md", *sorted((SKILL_DIR / "references").glob("*.md"))]


def requirement_items():
    """SKILL.md の「要件定義書を入れる」の番号付きの箇条から、9項目を正として読む。"""
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    section = text.split("### 要件定義書を入れる", 1)[1].split("###", 1)[0]
    return [f"{n}. {name}" for n, name in re.findall(r"^(\d)\. (\S+)$", section, re.M)]


def tags_examples():
    """文書のコードの箱と本文にある `--tags '<JSON>'` の例を、文書の名前と一緒に返す。"""
    for path in DOCS:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "--tags '" not in line or "<" in line.split("--tags", 1)[1][:3]:
                continue
            words = shlex.split(line.strip().strip("`"))
            for i, word in enumerate(words):
                if word == "--tags":
                    yield path.name, words[i + 1], "--block" in words


class DocsTests(unittest.TestCase):
    """文書の例が、CLI の検査と要件定義書の項目名に合っているかを見る。"""

    def setUp(self):
        self.items = requirement_items()
        self.vocabulary = tsuzuri._vocabulary(Path(tempfile.mkdtemp()))

    def test_skill_lists_nine_items(self):
        """正にする項目の一覧が読めていなければ、ほかの試験は何も確かめていない。"""
        self.assertEqual(len(self.items), 9, self.items)

    def test_tags_examples_pass_the_cli_check(self):
        """例の文機能が write の検査を通り、place が要件定義書の項目を番号と項目名で指している。"""
        examples = list(tags_examples())
        self.assertTrue(examples)
        for name, raw, block in examples:
            with self.subTest(doc=name, tags=raw):
                tags = json.loads(raw)
                if block:
                    tsuzuri._validate_block_tags(tags)
                else:
                    tsuzuri._validate_tags(tags, self.vocabulary)
                place = tags["place"]
                if not place.startswith("<"):
                    self.assertIn(place, self.items)

    def test_review_examples_start_with_a_known_aspect(self):
        """review の例の観点は、アプリが数え分ける頭の語で始める（無いと未解決に数えられない・Carbon #13 の2）。"""
        found = 0
        for path in DOCS:
            for raw in re.findall(r"--aspect '([^']+)'", path.read_text(encoding="utf-8")):
                if raw.startswith("<"):
                    continue
                found += 1
                with self.subTest(doc=path.name, aspect=raw):
                    self.assertRegex(raw, r"^(指摘|改善|推敲|対応)：")
        self.assertTrue(found)

    def test_bundled_templates_decide_register(self):
        """同梱のテンプレートは、使う場面の1行と、文体（口語か文語か）を決めた「文章の形の既定」を持つ。"""
        templates = sorted((SKILL_DIR / "references" / "templates").glob("*.md"))
        self.assertTrue(templates)
        for path in templates:
            with self.subTest(template=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.startswith(f"# {path.stem}\n"))
                rules = text.split("## 文章の形の既定", 1)[1].split("##", 1)[0]
                self.assertRegex(rules, r"文体: .*(口語|文語)")
                self.assertIn("## 骨組み", text)

    def test_references_name_the_same_nine_items(self):
        """references が挙げる項目名は、SKILL.md の9項目と同じ名前にする。"""
        names = {item.split(". ", 1)[1] for item in self.items}
        table = (SKILL_DIR / "references" / "requirements-and-design.md").read_text(encoding="utf-8")
        rows = re.findall(r"^\| (\d) \| ([^|]+?) \|", table, re.M)
        self.assertEqual([f"{n}. {name}" for n, name in rows], self.items)
        vocab = (SKILL_DIR / "references" / "tag-vocabulary.md").read_text(encoding="utf-8")
        for quoted in re.findall(r"「(\d\. [^」]+)」", vocab):
            self.assertIn(quoted.split(". ", 1)[1], names)


if __name__ == "__main__":
    unittest.main()
