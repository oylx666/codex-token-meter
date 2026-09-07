import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import settings
from watcher import Lifecycle


class SettingsTests(unittest.TestCase):
    def test_all_switch_combinations(self):
        for auto_open in (False,True):
            for auto_close in (False,True):
                life=Lifecycle()
                options=dict(auto_open=auto_open,auto_close=auto_close)
                self.assertEqual(life.update(True,**options),'start' if auto_open else None)
                self.assertIsNone(life.update(True,**options))
                self.assertIsNone(life.update(False,**options))
                self.assertEqual(life.update(False,**options),'stop' if auto_close else None)
                self.assertEqual(life.update(True,**options),'start' if auto_open else None)

    def test_enable_while_codex_open(self):
        life=Lifecycle()
        self.assertIsNone(life.update(True,auto_open=False))
        self.assertEqual(life.update(True,auto_open=True),'start')
        self.assertIsNone(life.update(True,auto_open=True))

    def test_persistent_and_invalid_settings(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(settings,'STATE_DIR',Path(folder)):
            self.assertEqual(settings.read_settings(),dict(auto_open=True,auto_close=True))
            settings.write_settings(auto_open=False)
            self.assertEqual(settings.read_settings(),dict(auto_open=False,auto_close=True))
            settings.write_settings(auto_close=False)
            self.assertFalse(settings.read_settings()['auto_open'])
            (Path(folder)/'lifecycle.json').write_text('{broken')
            self.assertTrue(settings.read_settings()['auto_open'])
            (Path(folder)/'lifecycle.json').write_text('{"auto_open":"false"}')
            self.assertTrue(settings.read_settings()['auto_open'])
            with self.assertRaises(ValueError):
                settings.write_settings(auto_close=1)
