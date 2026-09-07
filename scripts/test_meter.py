import json
from pathlib import Path
import tempfile
import unittest
import os
from usage import UsageReader, metrics
from catalog import Catalog, select_recent
from watcher import Lifecycle


def event(i=100, c=60, o=20):
    usage = dict(input_tokens=i, cached_input_tokens=c, output_tokens=o)
    return (json.dumps(dict(type='event_msg', timestamp='2026-09-07T00:00:00Z', payload=dict(type='token_count', info=dict(total_token_usage=usage, last_token_usage=usage)))) + '\n').encode()


class UsageTests(unittest.TestCase):
    def test_recent_session_switch_and_idle(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            sessions = root / 'sessions' / '2026' / '09' / '07'
            sessions.mkdir(parents=True)
            def make(name, source, modified):
                path = sessions / (name + '.jsonl')
                path.write_text(json.dumps(dict(type='session_meta', payload=dict(id=name, source=source, cwd=folder))) + '\n', encoding='utf-8')
                os.utime(path, (modified, modified))
                return path
            a = make('first', 'vscode', 100)
            b = make('second', 'vscode', 200)
            make('child', {'subagent': 'spawn'}, 300)
            (root / 'session_index.jsonl').write_text(json.dumps(dict(id='second', thread_name='Named task')) + '\n', encoding='utf-8')
            catalog = Catalog(root)
            self.assertEqual(select_recent(catalog.scan())['title'], 'Named task')
            self.assertEqual(select_recent(catalog.scan())['id'], 'second')
            os.utime(a, (400, 400))
            self.assertEqual(select_recent(catalog.scan())['id'], 'first')
            self.assertEqual(select_recent([]), None)

    def test_codex_start_close_reopen_and_manual_close(self):
        life = Lifecycle()
        self.assertIsNone(life.update(False))
        self.assertEqual(life.update(True), 'start')
        self.assertIsNone(life.update(True))
        # Closing the meter manually should not trigger a respawn loop.
        self.assertIsNone(life.update(True))
        self.assertIsNone(life.update(False))
        self.assertEqual(life.update(False), 'stop')
        self.assertEqual(life.update(True), 'start')

    def test_partial_and_duplicate_snapshots(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 's.jsonl'
            data = event()
            path.write_bytes(data[:-2])
            reader = UsageReader(path)
            reader.poll()
            self.assertIsNone(reader.info)
            with path.open('ab') as out:
                out.write(data[-2:] + data)
            reader.poll()
            self.assertEqual(metrics(reader.info['total_token_usage'])['input'], 100)
            self.assertEqual(metrics(reader.info['total_token_usage'])['ratio'], 60)
            path.write_bytes(b'')
            reader.poll()
            self.assertIsNone(reader.info)

    def test_missing_invalid_and_zero(self):
        self.assertIsNone(metrics({}))
        self.assertIsNone(metrics(dict(input_tokens=10, output_tokens=1, cached_input_tokens=11)))
        self.assertIsNone(metrics(dict(input_tokens=True, output_tokens=1, cached_input_tokens=0)))
        self.assertIsNone(metrics(dict(input_tokens=0, output_tokens=0, cached_input_tokens=0))['ratio'])

    def test_null_event_and_task_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / 'a', Path(folder) / 'b'
            a.write_bytes(event() + b'{"type":"event_msg","payload":{"type":"token_count","info":null}}\n')
            b.write_bytes(event(500, 0))
            reader = UsageReader(a)
            reader.poll()
            self.assertEqual(reader.info['total_token_usage']['input_tokens'], 100)
            reader = UsageReader(b)
            reader.poll()
            self.assertEqual(reader.info['total_token_usage']['input_tokens'], 500)


if __name__ == '__main__':
    unittest.main()
