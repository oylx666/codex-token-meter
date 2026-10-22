param([switch]$CloseMeter)
$ErrorActionPreference = 'Stop'
$shortcutPath = Join-Path ([Environment]::GetFolderPath('Startup')) 'Codex Token Meter Watcher.lnk'
if (Test-Path -LiteralPath $shortcutPath) { Remove-Item -LiteralPath $shortcutPath }
$stateDirectory = if ($env:CODEX_TOKEN_METER_STATE) { $env:CODEX_TOKEN_METER_STATE } else { Join-Path $env:LOCALAPPDATA 'CodexTokenMeter' }
New-Item -ItemType Directory -Path $stateDirectory -Force | Out-Null
[IO.File]::WriteAllText((Join-Path $stateDirectory 'stop-watcher'), [DateTime]::UtcNow.Ticks.ToString())
if ($CloseMeter) { [IO.File]::WriteAllText((Join-Path $stateDirectory 'close-request'), [DateTime]::UtcNow.Ticks.ToString()) }
Write-Output 'Autostart disabled. An existing meter window can be closed normally.'
