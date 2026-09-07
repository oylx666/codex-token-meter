"""Read-only session discovery. 'Recent activity' never means foreground page."""
import json
from pathlib import Path


class Catalog:
    def __init__(self, codex_dir):
        self.root = Path(codex_dir)
        self.meta = {}
        self.index_stamp = None
        self.names = {}

    def scan(self):
        try:
            index = self.root / 'session_index.jsonl'
            stat = index.stat()
            stamp = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
            if stamp != self.index_stamp:
                names = {}
                with index.open(encoding='utf-8', errors='replace') as stream:
                    for line in stream:
                        try:
                            row = json.loads(line)
                            if isinstance(row, dict) and isinstance(row.get('id'), str) and isinstance(row.get('thread_name'), str):
                                names[row['id']] = row['thread_name'][:500]
                        except (ValueError, TypeError, RecursionError):
                            pass
                self.names, self.index_stamp = names, stamp
        except OSError:
            pass
        rows, alive = [], set()
        for path in (self.root / 'sessions').glob('*/*/*/*.jsonl'):
            try:
                stat = path.stat()
                stamp = (stat.st_ino, stat.st_size, stat.st_mtime_ns)
                if path not in self.meta or self.meta[path][0] != stamp:
                    with path.open('rb') as stream:
                        line = stream.readline(1024 * 1024)
                    if not line.endswith(b'\n'):
                        continue
                    entry = json.loads(line)
                    if not isinstance(entry, dict) or entry.get('type') != 'session_meta':
                        continue
                    self.meta[path] = (stamp, entry.get('payload', {}))
                meta = self.meta[path][1]
                alive.add(path)
                if not isinstance(meta, dict):
                    continue
                source = meta.get('source')
                # Nested/subagent sessions must not steal automatic selection.
                if isinstance(source, dict) or source in ('exec', 'subagent'):
                    continue
                ident = meta.get('id')
                if not isinstance(ident, str) or not ident or not isinstance(meta.get('cwd', ''), str):
                    continue
                title = self.names.get(ident) or (Path(meta.get('cwd', '')).name + ' · ' + ident[-12:])
                if not isinstance(title, str):
                    title = ident
                title = ' '.join(title[:500].split())
                rows.append(dict(path=str(path), id=ident, title=title, cwd=meta.get('cwd', ''), modified=stat.st_mtime))
            except (OSError, ValueError, TypeError, RecursionError):
                continue
        self.meta = {path: value for path, value in self.meta.items() if path in alive}
        return sorted(rows, key=lambda row: (-row['modified'], row['id']))


def select_recent(rows):
    return rows[0] if rows else None
