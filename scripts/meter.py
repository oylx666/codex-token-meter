"""Codex-inspired local usage window. Standard library only; no network calls."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import queue
import re
import tkinter as tk
from tkinter import ttk, filedialog
import tkinter.font as tkfont

from common import CODEX_DIR, STATE_DIR, marker, read_state, save_state
from collector import Collector
from usage import UsageReader, metrics
from settings import read_settings, write_settings
from i18n import LANGUAGES, normalize_language, translate

THEMES = {
    '浅色': dict(bg='#ffffff', surface='#f5f5f5', text='#202020', muted='#707070', line='#e6e6e6', accent='#16805d', warning='#9b5b10'),
    '深色': dict(bg='#212121', surface='#2d2d2d', text='#eeeeee', muted='#aaaaaa', line='#414141', accent='#65c6a0', warning='#edbc77'),
}


def number(value):
    """Keep pathological counts inside the window; copy action preserves precision."""
    if value < 1_000_000:
        return f'{value:,}'
    for size, suffix in ((10**18, 'E'), (10**15, 'P'), (10**12, 'T'), (10**9, 'B'), (10**6, 'M')):
        if value >= size:
            return f'{value / size:.2f}{suffix}'


def elide(text, font, width):
    if font.measure(text) <= width:
        return text
    left, right = 0, len(text)
    while left < right:
        mid = (left + right + 1) // 2
        if font.measure(text[:mid] + '…') <= width:
            left = mid
        else:
            right = mid - 1
    return text[:left] + '…'


class Meter:
    def __init__(self, root, path=None, codex_dir=CODEX_DIR):
        self.root = root
        self.state = read_state()
        self.rows, self.snapshot = [], {}
        self.generation = 0
        self.closed = False
        self.picker = None
        self.close_stamp = marker('close-request')
        self.path = path or self.state.get('path')
        if not isinstance(self.path, str):
            self.path = None
        self.auto = tk.BooleanVar(value=False if path else self.state.get('auto') is not False)
        self.top = tk.BooleanVar(value=self.state.get('topmost') is True)
        lifecycle=read_settings()
        self.auto_open = tk.BooleanVar(value=lifecycle['auto_open'])
        self.auto_close = tk.BooleanVar(value=lifecycle['auto_close'])
        self.language = tk.StringVar(value=normalize_language(self.state.get('language')))
        self.scope = tk.StringVar(value='total')
        theme = self.state.get('theme', '浅色')
        self.theme = tk.StringVar(value=theme if theme in THEMES else '浅色')
        root.title('Codex Token Meter')
        root.minsize(620, 224)
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f'700x234+{max(0, sw-730)}+{max(0, sh-320)}')
        geometry = self.state.get('geometry')
        match = re.fullmatch(r'(\d+)x(\d+)([+-]\d+)([+-]\d+)', geometry) if isinstance(geometry, str) else None
        if match:
            width, height, x, y = map(int, match.groups())
            if 0 <= x < sw - 160 and 0 <= y < sh - 100:
                root.geometry(f'{min(max(width,620),sw)}x{min(max(height,224),sh)}+{x}+{y}')
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.bind('<Control-c>', lambda _: self.copy())
        root.bind('<Control-l>', lambda _: self.choose())
        self.font = tkfont.Font(family='Microsoft YaHei UI', size=9)
        self.build()
        self.collector = Collector(codex_dir)
        self.configure()
        self.tick()

    def t(self, text):
        return translate(text, self.language.get())

    def scope_label(self, scope=None):
        return self.t('任务累计' if (scope or self.scope.get()) == 'total' else '最近一次调用')

    def build(self):
        self.colors = THEMES[self.theme.get()]
        c = self.colors
        self.root.configure(bg=c['bg'])
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('TFrame', background=c['bg'])
        style.configure('TButton', background=c['surface'], foreground=c['text'], borderwidth=0, padding=(10, 6), font=('Microsoft YaHei UI', 9))
        style.map('TButton', background=[('active', c['line'])])
        style.configure('Treeview', background=c['bg'], fieldbackground=c['bg'], foreground=c['text'], rowheight=30, borderwidth=0, font=('Microsoft YaHei UI', 9))
        style.configure('Treeview.Heading', background=c['surface'], foreground=c['muted'], padding=8)
        style.map('Treeview', background=[('selected', c['line'])], foreground=[('selected', c['text'])])
        self.body = tk.Frame(self.root, bg=c['bg'])
        self.body.pack(fill='both', expand=True, padx=20, pady=14)
        header = tk.Frame(self.body, bg=c['bg'])
        header.pack(fill='x')
        tk.Label(header, text='Token Meter', bg=c['bg'], fg=c['text'], font=('Segoe UI', 12, 'bold')).pack(side='left')
        self.badge = tk.Label(header, text=self.t('● 自动跟随'), bg=c['bg'], fg=c['accent'], font=('Microsoft YaHei UI', 9))
        self.badge.pack(side='left', padx=14)
        ttk.Button(header, text='···', width=3, command=self.menu).pack(side='right')
        ttk.Button(header, text=self.t('任务'), command=self.choose).pack(side='right', padx=6)
        self.scope_button = ttk.Button(header, text=self.scope_label() + ' ▾', command=self.scope_menu)
        self.scope_button.pack(side='right')
        self.thread_label = tk.Label(self.body, text=self.t('正在读取最近会话…'), anchor='w', bg=c['bg'], fg=c['muted'], font=self.font)
        self.thread_label.pack(fill='x', pady=(9, 12))
        self.thread_label.bind('<Configure>', lambda _: self.render_title())
        tk.Frame(self.body, bg=c['line'], height=1).pack(fill='x')
        cards = tk.Frame(self.body, bg=c['bg'])
        cards.pack(fill='x', pady=(14, 12))
        self.values = []
        for col, title in enumerate([self.t('输入 token'), self.t('输出 token'), self.t('缓存输入'), self.t('缓存占比')]):
            card = tk.Frame(cards, bg=c['bg'])
            card.grid(row=0, column=col, sticky='ew', padx=(0 if col==0 else 12, 0))
            cards.columnconfigure(col, weight=1, uniform='metric')
            tk.Label(card, text=title, anchor='w', bg=c['bg'], fg=c['muted'], font=self.font).pack(fill='x')
            label = tk.Label(card, text='—', anchor='w', bg=c['bg'], fg=c['text'], font=('Segoe UI', -28, 'bold'))
            label.pack(fill='x', pady=(3, 0))
            self.values.append(label)
        footer = tk.Frame(self.body, bg=c['bg'])
        footer.pack(fill='x', side='bottom')
        self.status = tk.Label(footer, text=self.t('等待用量'), anchor='w', bg=c['bg'], fg=c['muted'], font=self.font)
        self.status.pack(side='left', fill='x', expand=True)
        tk.Label(footer, text=self.t('本地读取 · 0 模型调用'), bg=c['bg'], fg=c['muted'], font=('Microsoft YaHei UI', 8)).pack(side='right')
        self.root.attributes('-topmost', self.top.get())

    def configure(self):
        self.generation += 1
        self.collector.configure(self.generation, self.auto.get(), self.path)

    def mode(self):
        self.configure()
        self.save()

    def select(self, path):
        self.auto.set(False)
        self.path = str(path)
        self.snapshot = {}
        self.configure()
        self.render()
        self.save()

    def change_theme(self):
        if self.picker and self.picker.winfo_exists():
            self.picker.destroy()
        self.body.destroy()
        self.build()
        self.render()
        self.save()

    def new_menu(self):
        previous = getattr(self, '_popup', None)
        if previous is not None:
            previous.destroy()
        self._popup = tk.Menu(self.root, tearoff=False)
        return self._popup

    def menu(self):
        lifecycle=read_settings()
        self.auto_open.set(lifecycle['auto_open'])
        self.auto_close.set(lifecycle['auto_close'])
        menu = self.new_menu()
        menu.add_checkbutton(label=self.t('自动跟随最近更新的会话'), variable=self.auto, command=self.mode)
        menu.add_checkbutton(label=self.t('窗口置顶'), variable=self.top, command=self.pin)
        menu.add_separator()
        menu.add_checkbutton(label=self.t('随 Codex 打开浮窗'), variable=self.auto_open, command=self.lifecycle_settings)
        menu.add_checkbutton(label=self.t('随 Codex 关闭浮窗'), variable=self.auto_close, command=self.lifecycle_settings)
        menu.add_separator()
        for theme in THEMES:
            menu.add_radiobutton(label=self.t(theme + '外观'), variable=self.theme, value=theme, command=self.change_theme)
        menu.add_separator()
        languages = tk.Menu(menu, tearoff=False)
        for code, label in LANGUAGES.items():
            languages.add_radiobutton(label=label, variable=self.language, value=code, command=self.change_theme)
        menu.add_cascade(label=self.t('语言'), menu=languages)
        menu.add_separator()
        menu.add_command(label=self.t('复制精确统计  Ctrl+C'), command=self.copy)
        menu.add_command(label=self.t('打开会话文件…'), command=self.open_file)
        menu.add_command(label=self.t('打开使用说明'), command=self.help)
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()


    def lifecycle_settings(self):
        try:
            write_settings(auto_open=self.auto_open.get(),auto_close=self.auto_close.get())
            self.status.configure(text=self.t('联动设置已保存，监听器将在 3 秒内读取'))
        except OSError:
            self.status.configure(text=self.t('联动设置保存失败，请检查本地目录权限'))

    def scope_menu(self):
        menu = self.new_menu()
        for scope in ('total', 'last'):
            menu.add_radiobutton(label=self.scope_label(scope), variable=self.scope, value=scope, command=self.render)
        try:
            menu.tk_popup(self.root.winfo_pointerx(), self.root.winfo_pointery())
        finally:
            menu.grab_release()


    def pin(self):
        self.root.attributes('-topmost', self.top.get())
        self.save()

    def help(self):
        import os
        os.startfile(str(Path(__file__).resolve().parent.parent / ('README.en.md' if self.language.get() == 'en' else 'README.md')))

    def open_file(self):
        path = filedialog.askopenfilename(parent=self.root, title=self.t('选择会话文件'), initialdir=str(CODEX_DIR / 'sessions'), filetypes=[('Codex session', '*.jsonl')])
        if path:
            self.select(path)

    def choose(self):
        if self.picker and self.picker.winfo_exists():
            self.picker.lift()
            return
        dialog = self.picker = tk.Toplevel(self.root)
        dialog.title(self.t('选择任务'))
        dialog.configure(bg=self.colors['bg'])
        dialog.geometry('820x420')
        dialog.transient(self.root)
        search = tk.StringVar()
        entry = ttk.Entry(dialog, textvariable=search, font=self.font)
        entry.pack(fill='x', padx=16, pady=14)
        entry.focus_set()
        frame = ttk.Frame(dialog)
        frame.pack(fill='both', expand=True, padx=16)
        table = ttk.Treeview(frame, columns=('title', 'time'), show='headings', selectmode='browse')
        table.heading('title', text=self.t('任务名称 · 双击锁定'))
        table.heading('time', text=self.t('最近活动'))
        table.column('title', width=560)
        table.column('time', width=150, stretch=False)
        scroll = ttk.Scrollbar(frame, orient='vertical', command=table.yview)
        table.configure(yscrollcommand=scroll.set)
        table.pack(side='left', fill='both', expand=True)
        scroll.pack(side='right', fill='y')
        lookup = {}
        def fill(*_):
            table.delete(*table.get_children())
            lookup.clear()
            query = search.get().casefold()
            for row in self.rows:
                if query and query not in (row['title']+row['id']+row['cwd']).casefold():
                    continue
                try:
                    updated = datetime.fromtimestamp(row['modified']).strftime('%m-%d %H:%M')
                except (ValueError, OSError, OverflowError):
                    updated = self.t('未知时间')
                key = table.insert('', 'end', values=(row['title'], updated))
                lookup[key] = row
        def lock(*_):
            selected = table.selection()
            if selected:
                self.select(lookup[selected[0]]['path'])
                dialog.destroy()
        def follow():
            self.auto.set(True)
            self.mode()
            dialog.destroy()
        search.trace_add('write', fill)
        table.bind('<Double-1>', lock)
        table.bind('<Return>', lock)
        dialog.bind('<Escape>', lambda _: dialog.destroy())
        buttons = ttk.Frame(dialog)
        buttons.pack(fill='x', padx=16, pady=14)
        ttk.Button(buttons, text=self.t('自动跟随最新'), command=follow).pack(side='left')
        ttk.Button(buttons, text=self.t('锁定所选任务'), command=lock).pack(side='right')
        fill()

    def current_metrics(self):
        usage = self.snapshot.get('usage') or {}
        info = usage.get('info') or {}
        key = 'total_token_usage' if self.scope.get() == 'total' else 'last_token_usage'
        return metrics(info.get(key))

    def render_title(self):
        usage = self.snapshot.get('usage') or {}
        row = next((r for r in self.rows if r['path'] == usage.get('path')), None)
        text = row['title'] if row else (usage.get('thread_id') or self.t('等待本地会话记录'))
        self.thread_label.configure(text=elide(text, self.font, max(50,self.thread_label.winfo_width())))

    def render(self):
        data = self.current_metrics()
        values = [number(data[k]) for k in ('input','output','cached')] + [f"{data['ratio']:.1f}%" if data['ratio'] is not None else '—'] if data else ['—']*4
        for widget, value in zip(self.values, values):
            widget.configure(text=value)
        self.badge.configure(text=self.t('● 自动跟随') if self.auto.get() else self.t('● 已锁定'))
        self.scope_button.configure(text=self.scope_label() + ' ▾')
        self.render_title()
        usage = self.snapshot.get('usage') or {}
        error = self.snapshot.get('error') or usage.get('error')
        stamp = usage.get('timestamp')
        try:
            timestamp = datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone().strftime('%H:%M:%S') if isinstance(stamp,str) else self.t('未知')
        except (ValueError, OSError, OverflowError):
            timestamp = self.t('未知')
        message = self.t(error) if error else (self.t('正在加载历史记录…') if self.snapshot.get('loading') else (self.t('记录更新 ') + timestamp if data else self.t('等待有效用量记录')))
        self.status.configure(text=message, fg=self.colors['warning'] if error else self.colors['muted'])

    def copy(self):
        data = self.current_metrics()
        if not data:
            self.status.configure(text=self.t('尚无有效用量可复制'))
            return
        usage = self.snapshot.get('usage') or {}
        payload = dict(scope=self.scope.get(), thread_id=usage.get('thread_id'), timestamp=usage.get('timestamp'), **data)
        self.root.clipboard_clear()
        self.root.clipboard_append(json.dumps(payload, ensure_ascii=False, indent=2))
        self.status.configure(text=self.t('已复制精确统计'))

    def tick(self):
        if self.closed:
            return
        close_stamp = marker('close-request')
        if close_stamp and close_stamp != self.close_stamp:
            self.close()
            return
        try:
            value = self.collector.output.get_nowait()
            if value['generation'] == self.generation:
                self.snapshot, self.rows = value, value['rows']
                if value['usage']:
                    self.path = value['usage']['path']
                self.render()
        except queue.Empty:
            pass
        self.root.after(100, self.tick)

    def save(self):
        return save_state(dict(geometry=self.root.geometry(),topmost=self.top.get(),auto=self.auto.get(),path=self.path,theme=self.theme.get(),language=self.language.get()))

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.collector.stop.set()
        self.save()
        self.root.destroy()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session')
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--smoke-test', action='store_true')
    args = parser.parse_args()
    if args.inspect:
        if not args.session:
            parser.error('--inspect requires --session')
        reader = UsageReader(args.session)
        while reader.poll():
            pass
        print(json.dumps(reader.snapshot(), ensure_ascii=False))
        return
    from singleton import acquire
    instance_mutex = acquire('meter')
    if instance_mutex is None:
        return
    root = tk.Tk()
    app = Meter(root, args.session)
    if args.smoke_test:
        root.after(2000, app.close)
    root.mainloop()


if __name__ == '__main__':
    main()
