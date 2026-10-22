# Reliability review

## 0.2.2 — 2026-10-22

- Fixed lifecycle reconciliation when automatic closing is enabled after Codex already closed. An orphan meter is also closed after the startup debounce; minimizing remains a present window.
- Fixed upgrades leaving old code running: the installer requests a graceful restart and checks the new watcher's startup acknowledgment. A 10-second shutdown timeout is an explicit failure.
- Repeated-install testing uncovered a startup/shutdown race. The shutdown controller now repeats notifications while leases exist; watcher readiness is published after its shutdown baseline is initialized.
- Shared runtime discovery continues to the next Python candidate after a failed candidate instead of aborting on PowerShell native-command errors.
- Added paired Chinese and English README files and corrected the now-public repository's installation instructions.
- Validation: 27 local automated tests passed; theme/scale UI smoke checks passed; two consecutive installations completed successfully after the race fix. An earlier legacy pair did not respond to notifications and required a targeted restart of only the verified Token Meter processes. Normal upgrades do not force-kill processes.
- This is scoped regression evidence, not a claim that all possible defects are eliminated or that a signed, dependency-free installer exists.

## 0.2.0 review

## Fixed

- Disk scans and JSON parsing ran on the Tk thread. A single daemon collector now performs them off-thread; UI consumes only the latest bounded snapshot.
- Pending JSON grew indefinitely with an unterminated line. Reads are bounded to 1 MiB and pending lines to 4 MiB; oversized records are skipped with a visible warning until a valid usage event arrives.
- Malformed-record warnings disappeared on the next idle poll. They now persist until valid usage arrives. I/O failures are independently labeled as stale data.
- Same-path replacement and truncate/regrow could preserve old counters and metadata. Parser verifies an offset anchor and file identity; catalog refreshes changed metadata and prunes removed entries.
- Rapid manual selections could display an earlier worker result. Generation numbers now reject stale results.
- High font scaling could clip large counters. Counter glyph sizes and unit formatting are bounded; exact values remain available through Copy.
- Duplicate task dialogs and duplicated runtime lookup code were removed. Task picker is single-instance; PowerShell entrypoints share Runtime.ps1.
- Watcher now retries a failed launch, ignores missing control-marker files, and removes its PID file on normal stop.

## Verification

19 automated boundary tests pass on the development Windows machine: file replacement, truncation/regrowth, malformed/deep JSON, giant lines, randomized partial writes with UTF-8 and CRLF, permission failures, task isolation, rapid selection generations, process matching, lifecycle debounce, and a real cross-process Windows mutex.

UI smoke checks pass for both light and dark themes and Tk font scales 1.0, 1.5, and 2.0: long task titles, large counters, exact clipboard values, and a single task dialog. They validate widget geometry; they do not replace manual visual inspection or a full Windows multi-monitor/DPI certification.

## Remaining limits

- This is an unofficial companion window distributed as a Codex plugin package, not a native Codex status-bar extension.
- Recent file modification chooses the task; parallel parent tasks can switch the display. Pin a task when needed.
- No guarantee of per-token live updates, billing accuracy, cloud/remote coverage, or roll-up of child tasks.
- Local records are an internal data contract; future Codex format/process changes can require updates.
- Source distribution requires Python 3.9+ with Tkinter. A fresh-machine binary installer and signing are not part of this release.
- Named mutexes are session-local. Simultaneous Windows logins for the same user are not supported as a single shared UI session.
- The UI is newly restyled and geometry-tested. Final screenshot-based review of the updated window was unavailable after computer-use tooling stopped during this run.

## v0.3.0 — 2026-10-22

- Added English (default) and Simplified Chinese UI language selection with persisted preferences and matching user guides. Existing preferences without a language migrate to English.
- Kept metric scope IDs independent of translated labels; preserved task titles and exact numeric clipboard output. Parser errors are translated at the presentation boundary.
- Local validation: 30 unit tests; Tk smoke covering both languages, both themes, 3 font scales, language persistence/reload, stale-data translation, header/metric clipping, task picker, copy, and minimized/hidden window behavior. No screenshot-based visual review was performed.
- Native file dialog controls follow Windows settings. This remains an external Windows companion, dependent on Codex local log formats and process detection, not a native status-bar API.
