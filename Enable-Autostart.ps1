$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Runtime.ps1')
$pythonWindowless = Get-MeterPython
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
Start-Process -FilePath $pythonWindowless -ArgumentList ('"' + $watcherScript + '"') -WindowStyle Hidden
Write-Output "Enabled: $shortcutPath"
