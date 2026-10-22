function Get-MeterPython {
    $candidates = @()
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) { $candidates += $pythonCommand.Source }
    $pyCommand = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($pyCommand) { $candidates += $pyCommand.Source }
    foreach ($candidate in $candidates) {
        try {
            $runtimePath = & $candidate -c 'import sys, tkinter; assert sys.version_info >= (3,9); print(sys.executable)' 2>$null
        } catch { continue }
        if ($LASTEXITCODE -eq 0 -and $runtimePath) {
            $windowless = Join-Path (Split-Path $runtimePath.Trim()) 'pythonw.exe'
            if (Test-Path -LiteralPath $windowless) { return $windowless }
        }
    }
    throw 'Python 3.9+ with Tkinter is required. Install Python from python.org, then retry.'
}
