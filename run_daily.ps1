$ErrorActionPreference = "Stop"
$PSDefaultParameterValues["Out-File:Encoding"] = "utf8"; $PSDefaultParameterValues["Add-Content:Encoding"] = "utf8"
$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repo
$storage = Join-Path $env:LOCALAPPDATA "AI_Model_Watch"
$logDir = Join-Path $storage "logs"
$logPath = Join-Path $logDir "daily.log"
New-Item -ItemType Directory -Force $storage | Out-Null
New-Item -ItemType Directory -Force $logDir | Out-Null
$env:AI_MODEL_WATCH_DB = Join-Path $storage "ai_model_watch.db"
$env:UV_CACHE_DIR = Join-Path $storage "uv-cache"
New-Item -ItemType Directory -Force $env:UV_CACHE_DIR | Out-Null

"[$(Get-Date -Format o)] Starting official-site collection" | Add-Content $logPath
try {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        uv run --project . python -m ai_model_watch run-weekly --scope official --limit 100 *>> $logPath
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        python -m ai_model_watch run-weekly --scope official --limit 100 *>> $logPath
    } else {
        throw "Python or uv is required to run the daily pipeline."
    }
} catch {
    "[$(Get-Date -Format o)] ERROR: $($_.Exception.Message)" | Add-Content $logPath
    throw
} finally {
    "[$(Get-Date -Format o)] Official-site collection finished" | Add-Content $logPath
}
