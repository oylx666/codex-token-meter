"""Bounded incremental parser for native snapshots, never additive."""
import json
from pathlib import Path
import os

FIELDS = ('input_tokens', 'output_tokens', 'cached_input_tokens')


def metrics(value):
    if not isinstance(value, dict):
        return None
    if any(type(value.get(k)) is not int or not 0 <= value[k] <= 2**63-1 for k in FIELDS):
        return None
    i, o, c = (value[k] for k in FIELDS)
    if c > i:
        return None
    return dict(input=i, output=o, cached=c, ratio=c / i * 100 if i else None)


class UsageReader:
    CHUNK = 1024 * 1024
    MAX_LINE = 4 * 1024 * 1024

    def __init__(self, path):
        self.path = Path(path)
        self.reset()

    def reset(self):
        self.offset = 0
        self.pending = b''
        self.identity = None
        self.thread_id = None
        self.info = None
        self.timestamp = None
        self.error = None
        self.io_error = None
        self.discard = False
        self.anchor = b''
        self.last_stat = None

    def consume(self, line):
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                return
            payload = record.get('payload')
            if not isinstance(payload, dict):
                return
            if record.get('type') == 'session_meta':
                ident = payload.get('id')
                self.thread_id = ident if isinstance(ident, str) else None
            if record.get('type') != 'event_msg' or payload.get('type') != 'token_count':
                return
            info = payload.get('info')
            if info is None:
                return
            if not isinstance(info, dict):
                self.info = None
                self.error = '用量结构不兼容'
                return
            self.info = info
            self.timestamp = record.get('timestamp')
            self.error = None if metrics(info.get('total_token_usage')) else '用量字段缺失或异常'
        except (ValueError, UnicodeError, RecursionError):
            self.error = '部分记录损坏；等待下一条有效用量'

    def poll(self):
        try:
            with self.path.open('rb') as stream:
                stat = os.fstat(stream.fileno())
                identity = (stat.st_dev, stat.st_ino)
                changed = self.last_stat != (stat.st_size, stat.st_mtime_ns)
                rewrite = False
                if self.offset and changed:
                    stream.seek(max(0, self.offset - len(self.anchor)))
                    rewrite = stream.read(len(self.anchor)) != self.anchor
                    rewrite |= bool(stat.st_size == self.offset and self.last_stat and stat.st_mtime_ns != self.last_stat[1])
                if self.identity != identity or stat.st_size < self.offset or rewrite:
                    self.reset()
                    self.identity = identity
                stream.seek(self.offset)
                data = stream.read(self.CHUNK)
                self.offset = stream.tell()
                stream.seek(max(0, self.offset - 64))
                self.anchor = stream.read(min(64, self.offset))
                self.last_stat = (stat.st_size, stat.st_mtime_ns)
            self.io_error = None
            if self.discard:
                _, found, data = data.partition(b'\n')
                if not found:
                    return self.offset < stat.st_size
                self.discard = False
            lines = (self.pending + data).split(b'\n')
            self.pending = lines.pop()
            for line in lines:
                if len(line) > self.MAX_LINE:
                    self.error = '已跳过超大记录；等待下一条有效用量'
                elif line.strip():
                    self.consume(line)
            if len(self.pending) > self.MAX_LINE:
                self.pending = b''
                self.discard = True
                self.error = '已跳过超大记录；等待下一条有效用量'
            return self.offset < stat.st_size
        except OSError:
            self.io_error = '会话文件暂时不可读；显示的是上次记录'
            return False

    def snapshot(self):
        return dict(path=str(self.path), thread_id=self.thread_id, info=self.info,
                    timestamp=self.timestamp, error=self.io_error or self.error)
