"""Local UI translations. User content and machine-readable statistics stay unchanged."""
LANGUAGES = {'en': 'English', 'zh-CN': '简体中文'}
ENGLISH = {
    '● 自动跟随': '● Following',
    '● 已锁定': '● Pinned',
    '任务': 'Tasks',
    '任务累计': 'Session total',
    '最近一次调用': 'Last call',
    '正在读取最近会话…': 'Reading recent sessions…',
    '输入 token': 'Input tokens',
    '输出 token': 'Output tokens',
    '缓存输入': 'Cached input',
    '缓存占比': 'Cache ratio',
    '等待用量': 'Waiting for usage',
    '本地读取 · 0 模型调用': 'Local · No model calls',
    '自动跟随最近更新的会话': 'Follow most recently updated session',
    '窗口置顶': 'Always on top',
    '随 Codex 打开浮窗': 'Open with Codex',
    '随 Codex 关闭浮窗': 'Close with Codex',
    '浅色外观': 'Light appearance',
    '深色外观': 'Dark appearance',
    '复制精确统计  Ctrl+C': 'Copy exact statistics  Ctrl+C',
    '打开会话文件…': 'Open session file…',
    '打开使用说明': 'Open user guide',
    '联动设置已保存，监听器将在 3 秒内读取': 'Saved; applies within 3 seconds',
    '联动设置保存失败，请检查本地目录权限': 'Cannot save; check folder permissions',
    '选择会话文件': 'Choose a session file',
    '选择任务': 'Choose a task',
    '任务名称 · 双击锁定': 'Task name · Double-click to pin',
    '最近活动': 'Last activity',
    '未知时间': 'Unknown time',
    '自动跟随最新': 'Follow latest',
    '锁定所选任务': 'Pin selected task',
    '等待本地会话记录': 'Waiting for local session records',
    '未知': 'Unknown',
    '正在加载历史记录…': 'Loading history…',
    '记录更新 ': 'Updated ',
    '等待有效用量记录': 'Waiting for valid usage',
    '尚无有效用量可复制': 'No valid usage to copy',
    '已复制精确统计': 'Exact statistics copied',
    '用量结构不兼容': 'Unsupported usage format',
    '用量字段缺失或异常': 'Missing or invalid usage fields',
    '部分记录损坏；等待下一条有效用量': 'Damaged record; waiting for valid usage',
    '已跳过超大记录；等待下一条有效用量': 'Oversized record skipped; waiting for usage',
    '会话文件暂时不可读；显示的是上次记录': 'File unavailable; showing previous usage',
    '读取暂时失败：': 'Read failed: ',
    '语言': 'Language',
}


def normalize_language(value):
    return value if isinstance(value, str) and value in LANGUAGES else 'en'


def translate(text, language='en'):
    if normalize_language(language) == 'zh-CN':
        return text
    # Collector errors append a diagnostic exception name.
    prefix = '读取暂时失败：'
    if text.startswith(prefix):
        return ENGLISH[prefix] + text[len(prefix):]
    return ENGLISH.get(text, text)
