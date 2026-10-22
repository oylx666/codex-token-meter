# Codex Token Meter

[简体中文](README.md) | **English**

A local Windows companion window showing input tokens, output tokens, cached input tokens, and the cached-input percentage for the most recently updated Codex session. Light and dark themes are available.

**The running application makes no model calls and no network requests. It does not read `auth.json` or modify the Codex installation.** This is an unofficial companion distributed with a Codex plugin manifest, not a native Codex status-bar extension.

## Installation

1. Open the [public repository](https://github.com/oylx666/codex-token-meter) and select **Code → Download ZIP**. No invitation is required.
2. Extract it to a permanent directory. You may also use the source ZIP produced by the distribution script.
3. Install Python **3.9 or newer**, including Tcl/Tk (Tkinter), with `python` or `py` available on PATH.
4. Double-click `Install.cmd`. It creates a per-user Windows Startup shortcut and starts the watcher immediately. Administrator privileges are not required.
5. Open Codex normally. The meter usually appears within about three seconds. If you move the directory, run the installer again.

To upgrade, replace the files in the installation directory and run `Install.cmd` again. The installer requests a graceful shutdown of the old watcher and meter, starts the new watcher, and waits for a startup acknowledgment. A timeout is reported as an error; unrelated Python processes are not terminated.

This installs the local display and startup components. It does **not** automatically register the plugin in Codex's plugin catalog. The `.codex-plugin/plugin.json` manifest is included for plugin distribution; the companion can run independently.

## Usage

- While idle, the meter keeps showing the latest session's cumulative usage. It switches when another session file becomes the most recently updated. This follows file activity, **not the foreground Codex page**.
- `Session total` selects cumulative session usage; `Last call` selects the most recent model call, which is not necessarily a complete user turn.
- `Tasks` opens the searchable task list. Double-click a task to pin it, or restore automatic following from the list.
- The `···` menu contains always-on-top, light/dark appearance, exact-value copying, lifecycle switches, and advanced file selection. **Ctrl+C** copies statistics; **Ctrl+L** opens the task list.
- Large counts use M/B/T and larger units; copied values retain their exact integers. Missing values show a dash, and read failures are labeled as stale data.
- Closing the meter manually does not cause it to pop up repeatedly during the same Codex session. Run `Start.ps1` to reopen it manually, or restart Codex.

English is the default UI language. Choose **··· → Language → 简体中文** to switch to Simplified Chinese, or **··· → 语言 → English** to switch back. Changes apply immediately and persist across restarts. Menus, status messages, errors, and task picker labels follow the selected language; task titles and numeric data are unchanged. The user guide opens in the selected language. Native file dialog controls follow Windows language settings.

## Open/close integration

Two independent options in `···` are enabled by default:

| UI option | Behavior |
| --- | --- |
| Open with Codex | Open the meter when a Codex desktop window appears. |
| Close with Codex | Close the meter roughly 3–6 seconds after the last Codex desktop window closes, even if background processes remain. Minimizing does not count as closing. |

Settings are saved immediately and read by the watcher every three seconds. Disabling automatic opening does not close an existing meter; disabling automatic closing leaves it open. Enabling automatic closing after Codex has already closed also closes the meter. A newly started watcher cleans up an orphan meter after two absent-window checks. One transient missing-window check does not trigger closure.

These options require the watcher installed by `Install.cmd`. They cannot work if the Windows Startup entry is disabled and the watcher is not running.

A local command-line interface is also available; it makes no HTTP or model requests:

```powershell
python scripts/settings.py
python scripts/settings.py --auto-open on --auto-close on
python scripts/settings.py --auto-open off --auto-close off
```

Settings are stored in `%LOCALAPPDATA%/CodexTokenMeter/lifecycle.json`, separately from window preferences.

## Data and performance

The application reads the current user's `$CODEX_HOME/sessions` (default: `~/.codex/sessions`) and the task-name index. Cached input is a subset of input; its percentage is `cached input / input`. The latest cumulative snapshot is displayed directly: repeated snapshots are not summed, and reasoning tokens are not added again to reported output.

A background thread scans for sessions every three seconds and checks the selected file for new records every half-second. History is read in faster bounded chunks. Actual freshness depends on when Codex reports and writes usage. Reads are limited to 1 MiB per chunk and buffered records to 4 MiB. Skipped oversized records produce a warning until a valid usage event arrives.

Local state under `%LOCALAPPDATA%/CodexTokenMeter` includes window geometry, theme, language, and the selected session path. Running the meter consumes no model tokens. Developing it or asking Codex to operate or diagnose it still consumes normal conversation usage.

## Startup and removal

| Entry point | Purpose |
| --- | --- |
| `Install.cmd` | Install/restart the watcher and enable Windows login startup. |
| `Start.ps1` | Open only the meter. |
| `Uninstall.cmd` | Remove the Startup shortcut, signal the watcher to stop, and close the meter. Source files and preferences are retained. |
| `Disable-Autostart.ps1` | Disable startup and stop the watcher, leaving the meter open unless `-CloseMeter` is supplied. |

The shortcut is named `Codex Token Meter Watcher.lnk` in the current user's Windows Startup directory. The watcher remains in the background waiting for Codex after the meter closes. Uninstalling a Codex plugin alone does not remove this external shortcut: run `Uninstall.cmd` first.

## Development and checks

```powershell
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/ui_smoke.py
python scripts/package_release.py
```

UI smoke checks need a desktop session and use synthetic records in a temporary directory. The distribution script uses a file allowlist; it does not include real sessions, authentication files, local preferences, or Git history. Windows CI is configured for Python 3.9 and 3.12. Local test results and remote CI status are separate evidence.

## Troubleshooting and limitations

- No window: run `python scripts/watcher.py --probe`, check that `desktop_windows` is above zero and `auto_open` is true, and verify that Windows startup is enabled.
- Settings seem ineffective: ensure the watcher is running; rerun `Install.cmd` for a controlled restart.

Only Windows desktop sessions are supported. Parallel parent sessions can switch the automatic selection; pin one if necessary. Remote/cloud tasks, billing equivalence, and maintenance-free compatibility with future Codex releases are not guaranteed. This release still requires Python and does not provide a signed, runtime-bundled EXE installer. See [REVIEW.md](REVIEW.md) for the review record and remaining verification limits.
