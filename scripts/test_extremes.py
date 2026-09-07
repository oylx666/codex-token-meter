import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from usage import UsageReader, metrics
from catalog import Catalog
from collector import Collector
from watcher import is_codex_desktop, Lifecycle
from test_meter import event


class ParserExtremes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'session.jsonl'

    def load(self, data):
        self.path.write_bytes(data)
        reader = UsageReader(self.path)
        while reader.poll():
            pass
        return reader

    def test_warning_persists_and_recovers(self):
        reader = self.load(event() + b'{broken}\n')
        reader.poll()
        self.assertIsNotNone(reader.error)
        with self.path.open('ab') as stream:
            stream.write(event(200,100))
        reader.poll()
        self.assertIsNone(reader.error)
        self.assertEqual(reader.info['total_token_usage']['input_tokens'], 200)

    def test_missing_and_recreated_file(self):
        reader = self.load(event())
        self.path.unlink()
        reader.poll()
        self.assertIsNotNone(reader.io_error)
        self.path.write_bytes(event(300,0))
        reader.poll()
        self.assertIsNone(reader.io_error)
        self.assertEqual(reader.info['total_token_usage']['input_tokens'],300)

    def test_same_length_rewrite(self):
        reader = self.load(event(100,60))
        self.path.write_bytes(event(900,60))
        reader.poll()
        self.assertEqual(reader.info['total_token_usage']['input_tokens'],900)

    def test_truncate_regrow(self):
        reader = self.load(event())
        self.path.write_bytes(event(900,0) + b'{}\n'*100)
        reader.poll()
        self.assertEqual(reader.info['total_token_usage']['input_tokens'],900)

    def test_huge_unterminated_line_bounded(self):
        self.path.write_bytes(b'x'*(12*1024*1024))
        reader = UsageReader(self.path)
        while reader.poll():
            self.assertLessEqual(len(reader.pending), reader.MAX_LINE)
        self.assertIsNotNone(reader.error)
        with self.path.open('ab') as stream:
            stream.write(b'\n'+event())
        reader.poll()
        self.assertIsNone(reader.error)
        self.assertEqual(reader.info['total_token_usage']['input_tokens'],100)

    def test_huge_completed_line(self):
        reader = self.load(b'x'*(5*1024*1024)+b'\n'+event())
        self.assertEqual(reader.info['total_token_usage']['input_tokens'],100)

    def test_random_append_chunks_unicode_crlf(self):
        random.seed(31)
        self.path.write_bytes(b'')
        reader = UsageReader(self.path)
        data = ('{"text":"中文😀"}\r\n'.encode() + b''.join(event(i+100,60) for i in range(80)))
        offset = 0
        while offset < len(data):
            step = random.randint(1, 937)
            with self.path.open('ab') as stream:
                stream.write(data[offset:offset+step])
            reader.poll()
            offset += step
        self.assertEqual(reader.info['total_token_usage']['input_tokens'],179)

    def test_deep_json_invalid_types_and_nan(self):
        reader = self.load(b'['*2000+b']'*2000+b'\n'+event())
        self.assertIsNone(reader.error)
        for v in (True, -1, 1.3, '10', None, float('nan'), 2**64):
            self.assertIsNone(metrics(dict(input_tokens=v,output_tokens=0,cached_input_tokens=0)))

    def test_permission_failure_retains_stale_label(self):
        reader = self.load(event())
        with patch.object(Path,'open',side_effect=PermissionError):
            reader.poll()
        self.assertIsNotNone(reader.snapshot()['error'])
        self.assertIsNotNone(reader.info)

    def test_info_incompatible_clears_numbers(self):
        reader = self.load(event()+b'{"type":"event_msg","payload":{"type":"token_count","info":[]}}\n')
        self.assertIsNone(reader.info)
        self.assertIsNotNone(reader.error)


class DiscoveryExtremes(unittest.TestCase):
    def test_replaced_metadata_and_invalid_index(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            directory=root/'sessions/2026/01/01'
            directory.mkdir(parents=True)
            path=directory/'a.jsonl'
            def write(ident):
                path.write_text(json.dumps(dict(type='session_meta',payload=dict(id=ident,source='vscode'))) + '\n')
            write('old')
            (root/'session_index.jsonl').write_bytes(b'\xff\n{"id":[],"thread_name":7}\n')
            catalog=Catalog(root)
            self.assertEqual(catalog.scan()[0]['id'],'old')
            write('new')
            self.assertEqual(catalog.scan()[0]['id'],'new')
            path.unlink()
            self.assertEqual(catalog.scan(),[])
            self.assertEqual(catalog.meta,{})

    def test_worker_generation_and_close(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'selected'
            path.write_bytes(event())
            worker=Collector(folder)
            try:
                for generation in range(20):
                    worker.configure(generation,False,str(path))
                deadline=time.monotonic()+5
                found=False
                while time.monotonic()<deadline:
                    snapshot=worker.output.get(timeout=2)
                    if snapshot['generation']==19:
                        self.assertEqual(snapshot['usage']['info']['total_token_usage']['input_tokens'],100)
                        found=True
                        break
                self.assertTrue(found)
            finally:
                worker.stop.set()
                worker.thread.join(timeout=2)
            self.assertFalse(worker.thread.is_alive())

    def test_app_detection_and_debounce(self):
        self.assertTrue(is_codex_desktop(r'C:\Program Files\WindowsApps\OpenAI.Codex_26.999_x64\app\ChatGPT.exe'))
        self.assertFalse(is_codex_desktop(r'C:\Users\name\AppData\Local\OpenAI\Codex\bin\hash\codex.exe'))
        self.assertFalse(is_codex_desktop(r'C:\Program Files\ChatGPT\ChatGPT.exe'))
        life=Lifecycle()
        self.assertEqual(life.update(True),'start')
        self.assertIsNone(life.update(False))
        self.assertIsNone(life.update(True))

    @unittest.skipUnless(sys.platform=='win32','Windows mutex')
    def test_cross_process_mutex(self):
        from singleton import acquire
        handle=acquire('test-suite-'+str(os.getpid()))
        self.assertTrue(handle)
        code="from singleton import acquire; assert acquire('test-suite-"+str(os.getpid())+"') is None"
        result=subprocess.run([sys.executable,'-c',code],cwd=Path(__file__).parent,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':
    unittest.main()
