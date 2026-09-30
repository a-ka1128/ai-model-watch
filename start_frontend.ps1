$ErrorActionPreference = "Stop"
$PSDefaultParameterValues["Out-File:Encoding"] = "utf8"; $PSDefaultParameterValues["Add-Content:Encoding"] = "utf8"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $repo "frontend"
$storage = Join-Path $env:LOCALAPPDATA "AI_Model_Watch"
$logDir = Join-Path $storage "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$logPath = Join-Path $logDir "frontend.log"

Set-Location $frontend
"[$(Get-Date -Format o)] Starting AI Model Watch dashboard" | Add-Content $logPath
try {
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if (-not $nodeCommand) { throw "node.exe was not found." }
    $nextCli = Join-Path $frontend "node_modules\next\dist\bin\next"
    if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
        npm install --no-audit --no-fund *>> $logPath
    }
    if (-not (Test-Path (Join-Path $frontend ".next"))) {
        npm run build *>> $logPath
    }
    & $nodeCommand.Source $nextCli start --hostname 127.0.0.1 --port 3000 *>> $logPath
} finally {
    "[$(Get-Date -Format o)] AI Model Watch dashboard stopped" | Add-Content $logPath
}
