$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonLauncher = Get-Command py.exe -ErrorAction SilentlyContinue
if (-not $pythonLauncher) { throw "Windows Python launcher (py.exe) was not found." }

Set-Location $repo
& $pythonLauncher.Source -3.11 (Join-Path $repo "control_panel.py")
