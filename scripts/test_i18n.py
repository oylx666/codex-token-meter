import ast
from pathlib import Path
import unittest

from i18n import normalize_language, translate


class LocalizationTests(unittest.TestCase):
    def test_invalid_preferences_fall_back_to_english(self):
        for value in (None, '', 'fr', [], {}, 42):
            self.assertEqual(normalize_language(value), 'en')
        self.assertEqual(normalize_language('zh-CN'), 'zh-CN')

    def test_all_parser_errors_have_english_translations(self):
        for name in ('usage.py', 'collector.py'):
            tree = ast.parse(Path(__file__).with_name(name).read_text(encoding='utf-8'))
            messages = [node.value for node in ast.walk(tree)
                        if isinstance(node, ast.Constant) and isinstance(node.value, str)
                        and any('\u4e00' <= ch <= '\u9fff' for ch in node.value)]
            self.assertTrue(messages)
            for message in messages:
                self.assertFalse(any('\u4e00' <= ch <= '\u9fff' for ch in translate(message)))
                self.assertEqual(translate(message, 'zh-CN'), message)

    def test_diagnostics_preserve_exception_details(self):
        self.assertEqual(translate('读取暂时失败：PermissionError'), 'Read failed: PermissionError')
        self.assertEqual(translate('Unknown future diagnostic'), 'Unknown future diagnostic')
