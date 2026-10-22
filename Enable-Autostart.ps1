$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Runtime.ps1')
$pythonWindowless = Get-MeterPython
$pythonConsole = Join-Path (Split-Path $pythonWindowless) 'python.exe'
& $pythonConsole (Join-Path $PSScriptRoot 'scripts\control.py') --stop
if ($LASTEXITCODE -ne 0) { throw 'Previous Token Meter instance did not stop. Installation was not completed.' }
$watcherScript = Join-Path $PSScriptRoot 'scripts\watcher.py'
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'Codex Token Meter Watcher.lnk'
$shortcutShell = New-Object -ComObject WScript.Shell
$shortcut = $shortcutShell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonWindowless
$shortcut.Arguments = '"' + $watcherScript + '"'
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = 'Start token meter when Codex desktop starts; local only'
$shortcut.WindowStyle = 7
$shortcut.Save()
$watcherProcess = Start-Process -FilePath $pythonWindowless -ArgumentList ('"' + $watcherScript + '"') -WindowStyle Hidden -PassThru
$meterState = if ($env:CODEX_TOKEN_METER_STATE) { $env:CODEX_TOKEN_METER_STATE } else { Join-Path $env:LOCALAPPDATA 'CodexTokenMeter' }
$pidFile = Join-Path $meterState 'watcher.pid'
$ready = $false
$deadline = [DateTime]::UtcNow.AddSeconds(8)
do {
    if ($watcherProcess.HasExited) { throw 'Token Meter watcher exited during startup.' }
    if (Test-Path -LiteralPath $pidFile) {
        $recordedPid = Get-Content -LiteralPath $pidFile -Raw -ErrorAction SilentlyContinue
        if ($recordedPid -and $recordedPid.Trim() -eq $watcherProcess.Id.ToString()) { $ready = $true; break }
    }
    Start-Sleep -Milliseconds 100
} while ([DateTime]::UtcNow -lt $deadline)
if (-not $ready) { throw 'Token Meter watcher did not acknowledge startup within 8 seconds.' }
Write-Output "Enabled: $shortcutPath"
