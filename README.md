# Codex Token Meter

**简体中文** | [English](README.en.md)

Windows 本地 token 统计浮窗。白色／深灰界面，自动展示最近更新会话的输入、输出、缓存输入 token 和缓存占比。

**独立本地程序，不调用模型、不访问网络，不读取 auth.json，也不修改 Codex 安装文件。** 这是非官方伴随工具；插件包负责分发，浮窗不属于 Codex 原生底部栏。

## 如何安装

1. 打开[公开 GitHub 仓库](https://github.com/oylx666/codex-token-meter)，通过 Code → Download ZIP 下载源码，无需邀请。
2. 下载代码 ZIP 并解压到固定目录。也可以直接接收拥有者提供的源码分发 ZIP。
3. 安装 Python 3.9 或更高版本，包含 Tcl/Tk（Tkinter），确保 `python` 或 `py` 命令可用。
4. 双击 `Install.cmd`。它创建当前用户的启动项并立即运行监听器，无需管理员权限。
5. 正常打开 Codex，浮窗通常三秒左右自动出现。请不要移动已安装目录；移动后重新运行安装脚本。

升级时用新版文件替换安装目录，再运行 `Install.cmd`。安装器会先请求旧监听器和旧浮窗正常退出，再启动新版，并确认监听器已启动；超时会明确报错，不再只创建快捷方式就声称安装成功。它不会结束其他 Python 程序。

这个安装入口安装的是本地显示和自启动组件，不会自动注册 Codex 的插件目录。`.codex-plugin/plugin.json` 同时保留为插件分发入口；无论是否注册插件，显示组件都可独立运行。

## 使用

- 空闲时显示最新会话的累计用量，另一会话有记录更新时自动切换。自动选择依据文件更新，不识别前台页面。
- `任务累计` 可切换到 `最近一次调用`，后者不等于用户消息的完整一轮。
- `任务` 打开可搜索列表，双击锁定；列表底部可恢复自动跟随。
- `···` 菜单提供置顶、浅色／深色、复制精确统计和高级文件选择。Ctrl+C 复制，Ctrl+L 打开任务列表。
- 大数使用 M/B/T 等单位，复制结果保留完整整数。缺失数据为破折号，读取失败会标注旧数据。
- 手动关闭浮窗后，本次 Codex 运行期间不反复弹出。可运行 Start.ps1 手动重开；下次启动 Codex 自动恢复。

## 数据与性能

只读取当前用户的 `$CODEX_HOME/sessions`（默认 `~/.codex/sessions`）及任务名称索引。缓存是输入的子集；占比为缓存输入 / 输入。直接展示最新累计快照，不将重复快照相加，也不再次叠加 reasoning token。

后台线程每三秒扫描会话目录，每半秒检查选中会话的增量数据；加载历史时会加快分块读取。准确更新时间取决于 Codex 上报和落盘。单次读取最多 1 MiB，单条记录缓存最多 4 MiB。大型记录被跳过时会提示，直到下一条有效用量到达。

状态保存在 `%LOCALAPPDATA%/CodexTokenMeter`，包含窗口位置、外观和选择路径。运行时无模型调用；开发、通过对话操作或诊断插件仍属于正常 Codex 对话用量。

## 启动与卸载

### 启动、关闭联动开关

浮窗右上角 `···` 菜单提供两个独立选项，默认均开启：

- **随 Codex 打开浮窗**：出现 Codex 桌面窗口时打开浮窗。手动关闭浮窗后不会每次检测都重新弹出。
- **随 Codex 关闭浮窗**：最后一个 Codex 桌面窗口关闭后，约三至六秒关闭浮窗。最小化不算关闭；即使 Codex 后台进程仍驻留也可以联动关闭。

设置立即保存，监听器每三秒读取。关闭“自动打开”不终止已经显示的窗口；关闭“自动关闭”后浮窗会保留。设置依赖 Install.cmd 安装的监听器，自启动项被禁用时不生效。

如果 Codex 已经关闭，此时开启“自动关闭”也会关闭浮窗。监听器刚启动且没有 Codex 窗口时，会在两次检查后清理遗留浮窗。最小化或一次短暂的窗口缺失不会触发关闭。

也可通过本地命令行接口查看、修改，不涉及 HTTP 或模型调用：

```powershell
python scripts/settings.py
python scripts/settings.py --auto-open on --auto-close on
python scripts/settings.py --auto-open off --auto-close off
```

设置文件是 `%LOCALAPPDATA%/CodexTokenMeter/lifecycle.json`，与窗口外观状态分开保存。

- Install.cmd：安装自启动；监听器检测 Codex 桌面进程后显示窗口。
- Start.ps1：仅打开浮窗。
- Uninstall.cmd：移除启动项，停止监听器并关闭浮窗，保留源码和窗口偏好。
- Disable-Autostart.ps1：仅取消自动启动，默认保留已打开的浮窗。

启动项名为 `Codex Token Meter Watcher.lnk`，位于 Windows 当前用户 Startup 目录。关闭浮窗后监听器继续等待下一次启动。卸载 Codex 插件本身不会移除这个外部启动项，需先运行 Uninstall.cmd。

## 开发与验证

```powershell
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/ui_smoke.py
python scripts/package_release.py
```

UI 测试需要桌面会话，仅使用临时合成记录。测试状态和数据不进入分发包。分发脚本使用文件白名单，不打包真实会话、授权文件或 Git 历史。仓库包含 Windows Python 3.9/3.12 CI 配置；本机测试结果与尚未运行的远程 CI 分开记录。

详细缺陷、修复和未验证边界见 [REVIEW.md](REVIEW.md)。目前仍需 Python，没有捆绑运行环境的签名 EXE 安装包。未来 Codex 数据格式或进程布局改变时可能需要适配。

### 排障

- 不弹出：先运行 `python scripts/watcher.py --probe`，检查 `desktop_windows` 是否大于 0、`auto_open` 是否为 true，并检查 Windows 启动项是否启用。
- 修改选项没有效果：确认监听器仍在运行；重新运行 `Install.cmd` 可完成一次受控重启。
- 没有统计：新会话可能还没有落盘的用量事件；不要把破折号理解为零消耗。
- 检测不到新版本 Codex：进程路径或内部会话格式可能已改变，请附上版本和错误描述提 issue，勿上传 auth.json 或真实会话。

目前仅支持 Windows 桌面版；不覆盖远程／云端任务，也不保证账单一致或未来 Codex 升级零维护。
