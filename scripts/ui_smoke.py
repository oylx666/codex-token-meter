"""Run with a desktop session. Fixtures and state stay in a temporary directory."""
import json
import os
from pathlib import Path
import tempfile
import time


def run():
    with tempfile.TemporaryDirectory() as folder:
        os.environ['CODEX_TOKEN_METER_STATE'] = str(Path(folder)/'state')
        os.environ['CODEX_HOME'] = str(Path(folder)/'codex')
        from meter import Meter, THEMES, number
        from test_meter import event
        import tkinter as tk
        directory=Path(os.environ['CODEX_HOME'])/'sessions/2026/01/01'
        directory.mkdir(parents=True)
        path=directory/'test.jsonl'
        path.write_bytes(b'{"type":"session_meta","payload":{"id":"fixture","source":"vscode"}}\n'+event(2**60,2**59,2**40))
        (directory.parents[3]/'session_index.jsonl').write_text(json.dumps(dict(id='fixture',thread_name='超长标题边界测试 '*100))+'\n',encoding='utf-8')
        root=tk.Tk()
        try:
            clipboard_before=root.clipboard_get()
        except tk.TclError:
            clipboard_before=''
        app=Meter(root)
        errors=[]
        root.report_callback_exception=lambda *exc: errors.append(str(exc))
        def pump(seconds=0.1):
            deadline=time.monotonic()+seconds
            while time.monotonic()<deadline:
                root.update()
                time.sleep(.01)
        try:
            pump(1.2)
            assert app.current_metrics()['input']==2**60
            assert app.language.get() == 'en', 'Fresh installation must default to English'
            from common import read_state
            for language in ('zh-CN', 'en'):
                app.language.set(language)
                app.change_theme()
                assert read_state()['language'] == language
                assert app.scope_button.cget('text') == app.scope_label() + ' ▾'
                app.menu()
                pump()
                popup = app._popup
                assert popup.winfo_exists(), 'Menu must remain available after posting'
                popup.unpost()
                app.scope_menu()
                pump()
                assert app._popup.winfo_exists()
                app._popup.unpost()
                app.scope.set('last')
                app.render()
                assert app.current_metrics()['input'] == 2**60
                app.snapshot['error'] = '会话文件暂时不可读；显示的是上次记录'
                app.render()
                assert app.status.cget('text') == app.t(app.snapshot['error'])
                assert ('previous usage' in app.status.cget('text')) == (language == 'en')
                app.snapshot.pop('error')
                app.scope.set('total')
            for language, scaling in ((lang, scale) for lang in ('en', 'zh-CN') for scale in (1.0, 1.5, 2.0)):
                app.language.set(language)
                root.tk.call('tk','scaling',scaling)
                for theme in THEMES:
                    app.theme.set(theme)
                    app.change_theme()
                    root.geometry('700x260')
                    pump()
                    for widget in app.scope_button.master.winfo_children():
                        assert widget.winfo_width() >= widget.winfo_reqwidth(), 'Header text clipped'
                    for value in app.values:
                        assert value.winfo_reqwidth() <= value.winfo_width(), 'Metric text clipped'
                        assert value.winfo_rooty()+value.winfo_height() <= root.winfo_rooty()+root.winfo_height()
                    assert app.font.measure(app.thread_label.cget('text')) <= app.thread_label.winfo_width()
                    app.choose()
                    pump()
                    picker=app.picker
                    app.choose()
                    assert app.picker is picker, 'Duplicate picker'
                    picker.destroy()
            app.copy()
            assert json.loads(root.clipboard_get())['input']==2**60
            assert number(999999)=='999,999'
            assert number(10**12)=='1.00T'
            assert not errors, errors
            from watcher import desktop_window_count
            assert desktop_window_count([os.getpid()]) == 1
            root.iconify()
            pump()
            assert desktop_window_count([os.getpid()]) == 1, 'Minimize must not count as closed'
            root.withdraw()
            pump()
            assert desktop_window_count([os.getpid()]) == 0, 'No desktop window must count as closed'
            root.deiconify()
            pump()
            print('UI PASS: English/Chinese switching and persistence, both themes, long title, huge counts, 3 font scales, singleton picker, exact copy')
        finally:
            root.clipboard_clear()
            root.clipboard_append(clipboard_before)
            app.close()
            app.collector.thread.join(2)
        # A new process-equivalent UI reads the saved language, not the default.
        second_root = tk.Tk()
        second = Meter(second_root)
        try:
            assert second.language.get() == 'zh-CN'
        finally:
            second.close()
            second.collector.thread.join(2)


if __name__=='__main__':
    run()
