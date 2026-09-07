"""One daemon worker keeps disk I/O and JSON decoding off Tk's UI thread."""
import queue
import threading
import time
from catalog import Catalog, select_recent
from usage import UsageReader


class Collector:
    def __init__(self, codex_dir):
        self.catalog = Catalog(codex_dir)
        self.commands = queue.Queue()
        self.output = queue.Queue(maxsize=1)
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True, name='usage-reader')
        self.thread.start()

    def configure(self, generation, auto, path):
        self.commands.put((generation, auto, path))

    def run(self):
        reader, rows, generation, auto, scan_at = None, [], -1, True, 0
        while not self.stop.is_set():
            loading, error = False, None
            try:
                while True:
                    try:
                        generation, auto, path = self.commands.get_nowait()
                        if path and (reader is None or str(reader.path) != path):
                            reader = UsageReader(path)
                        scan_at = 0
                    except queue.Empty:
                        break
                if time.monotonic() >= scan_at:
                    rows = self.catalog.scan()
                    scan_at = time.monotonic() + 3
                recent = select_recent(rows)
                if auto and recent and (reader is None or str(reader.path) != recent['path']):
                    reader = UsageReader(recent['path'])
                if reader:
                    loading = reader.poll()
            except Exception as exc:
                error = '读取暂时失败：' + type(exc).__name__
            value = dict(generation=generation, rows=rows, usage=reader.snapshot() if reader else None, loading=loading, error=error)
            try:
                self.output.get_nowait()
            except queue.Empty:
                pass
            self.output.put_nowait(value)
            self.stop.wait(0.02 if loading else 0.5)
