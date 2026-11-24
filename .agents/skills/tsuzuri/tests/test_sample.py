"""C#14: 見本は完成してから入れ替え、失敗時には前の記録を残す。"""

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[3] / "app/sample/make_sample.py"
SPEC = importlib.util.spec_from_file_location("make_sample", SCRIPT)
sample = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sample)


class SampleTests(unittest.TestCase):
    """作り直しの成功・生成失敗・入れ替え失敗を一時フォルダで検査する。"""

    def test_rebuild_and_failure_keep_a_complete_sample(self):
        """現行の見出しと対応要件で完成し、個人パスを除き、生成失敗でも既存記録を保つ。"""
        with tempfile.TemporaryDirectory() as directory:
            here = Path(directory)
            document = here / "構想.md"
            root = here / "構想.md.tsuzuri"
            root.mkdir()
            (root / "old").write_text("前の見本", encoding="utf-8")
            with patch.object(sample, "HERE", here), patch.object(sample, "DOC", document), patch.object(sample, "ROOT", root):
                with patch.object(sample, "REQUIREMENTS", "旧形式の不正な要件"):
                    with self.assertRaises(SystemExit):
                        sample.main()
                self.assertEqual((root / "old").read_text(encoding="utf-8"), "前の見本")
                sample.main()
                order = json.loads((root / "order.json").read_text(encoding="utf-8"))
                self.assertEqual(order["document"], "構想.md")
                self.assertEqual(len(order["order"]), 6)
                self.assertEqual(sample.run("check", str(root)), "")
                requirements = (root / "requirements/r001.md").read_text(encoding="utf-8")
                for sid in order["order"]:
                    latest = sorted((root / "sentences" / sid).glob("v[0-9]*.json"))[-1]
                    tags = json.loads(latest.read_text(encoding="utf-8"))["tags"]
                    self.assertIn("## " + tags["place"] + "\n", requirements)
                previous = (root / "order.json").read_bytes()
                rename = Path.rename

                def fail_install(source, destination):
                    if source.name == root.name and source.parent != here:
                        raise OSError("入れ替え失敗")
                    return rename(source, destination)

                with patch.object(Path, "rename", fail_install), self.assertRaises(OSError):
                    sample.main()
                self.assertEqual((root / "order.json").read_bytes(), previous)
                self.assertEqual(list(here.glob(".sample-*")), [])

                def fail_install_and_restore(source, destination):
                    if source.parent != here:
                        raise OSError("入れ替えと復元に失敗")
                    return rename(source, destination)

                with patch.object(Path, "rename", fail_install_and_restore), self.assertRaises(OSError):
                    sample.main()
                backup = next(here.glob(".sample-*/previous"))
                self.assertEqual((backup / "order.json").read_bytes(), previous)
                backup.rename(root)
            self.assertFalse(document.exists())
