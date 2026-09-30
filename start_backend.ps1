$ErrorActionPreference = "Stop"
$PSDefaultParameterValues["Out-File:Encoding"] = "utf8"; $PSDefaultParameterValues["Add-Content:Encoding"] = "utf8"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$storage = Join-Path $env:LOCALAPPDATA "AI_Model_Watch"
$logDir = Join-Path $storage "logs"
New-Item -ItemType Directory -Force $logDir | Out-Null
$logPath = Join-Path $logDir "backend.log"

Set-Location $repo
$env:AI_MODEL_WATCH_DB = Join-Path $storage "ai_model_watch.db"
$env:PYTHONUNBUFFERED = "1"
$env:UV_CACHE_DIR = Join-Path $storage "uv-cache"
New-Item -ItemType Directory -Force $env:UV_CACHE_DIR | Out-Null
$uvCommand = Get-Command uv -ErrorAction SilentlyContinue
$uvPath = if ($uvCommand) { $uvCommand.Source } else { Join-Path $env:USERPROFILE ".local\bin\uv.exe" }
if (-not (Test-Path $uvPath)) { throw "uv was not found at $uvPath" }

"[$(Get-Date -Format o)] Starting AI Model Watch API" | Add-Content $logPath
try {
    & $uvPath run --project $repo --extra api python -m uvicorn ai_model_watch.api:create_app --factory --host 127.0.0.1 --port 8000 *>> $logPath
} finally {
    "[$(Get-Date -Format o)] AI Model Watch API stopped" | Add-Content $logPath
}
