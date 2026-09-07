param([string]$SessionPath)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'Runtime.ps1')
$pythonWindowless = Get-MeterPython
$meterScript = Join-Path $PSScriptRoot 'scripts\meter.py'
$launchArguments = @('"' + $meterScript + '"')
if ($SessionPath) { $launchArguments += @('--session', '"' + $SessionPath + '"') }
Start-Process -FilePath $pythonWindowless -ArgumentList $launchArguments -WindowStyle Hidden
