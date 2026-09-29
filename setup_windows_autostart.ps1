param(
    [switch]$SkipInstall,
    [switch]$StartNow
)
$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendScript = Join-Path $repo "start_backend.ps1"
$frontendScript = Join-Path $repo "start_frontend.ps1"
$weeklyScript = Join-Path $repo "run_weekly.ps1"
$panelScript = Join-Path $repo "start_control_panel.ps1"
$hiddenLauncher = Join-Path $repo "run_hidden.vbs"
$panelExe = Join-Path $repo "dist\AI_Model_Watch_Control_Panel.exe"
$env:UV_CACHE_DIR = Join-Path (Join-Path $env:LOCALAPPDATA "AI_Model_Watch") "uv-cache"
New-Item -ItemType Directory -Force $env:UV_CACHE_DIR | Out-Null
$powershell = (Get-Command powershell.exe).Source
$wscript = Join-Path $env:WINDIR "System32\wscript.exe"
$nodePath = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
$nextCli = Join-Path (Join-Path $repo "frontend") "node_modules\next\dist\bin\next"
$userId = "$env:USERDOMAIN\$env:USERNAME"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install uv first, then run this script again."
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "npm is required. Install Node.js first, then run this script again."
}

if (-not $SkipInstall) {
    Push-Location $repo
    try {
        uv sync --extra api
        Push-Location (Join-Path $repo "frontend")
        try { npm install --no-audit --no-fund } finally { Pop-Location }
    } finally { Pop-Location }
}

$settings = New-ScheduledTaskSettingsSet -Hidden -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$logon = New-ScheduledTaskTrigger -AtLogOn -User $userId
$weekly = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 9:00AM

function Register-AIModelWatchTask([string]$name, [string]$scriptPath, $trigger) {
    if ($name -eq "AI Model Watch - Frontend" -and $nodePath -and (Test-Path $nextCli)) {
        $argument = "`"$nextCli`" start --hostname 127.0.0.1 --port 3000"
        $action = New-ScheduledTaskAction -Execute $nodePath -Argument $argument -WorkingDirectory (Join-Path $repo "frontend")
    } elseif ($name -eq "AI Model Watch - Control Panel" -and (Test-Path $panelExe)) {
        $action = New-ScheduledTaskAction -Execute $panelExe -WorkingDirectory $repo
    } else {
        $argument = "`"$hiddenLauncher`" `"$scriptPath`""
        $action = New-ScheduledTaskAction -Execute $wscript -Argument $argument -WorkingDirectory $repo
    }
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "AI Model Watch automatic task" -Force | Out-Null
    Write-Output "Registered: $name"
}

Register-AIModelWatchTask "AI Model Watch - Backend" $backendScript $logon
Register-AIModelWatchTask "AI Model Watch - Frontend" $frontendScript $logon
Register-AIModelWatchTask "AI Model Watch - Weekly Pipeline" $weeklyScript $weekly
Register-AIModelWatchTask "AI Model Watch - Control Panel" $panelScript $logon

if ($StartNow) {
    Start-ScheduledTask -TaskName "AI Model Watch - Backend"
    Start-ScheduledTask -TaskName "AI Model Watch - Frontend"
    Write-Output "Started backend and frontend. Open http://127.0.0.1:3000"
} else {
    Write-Output "Autostart configured. It will run after the next Windows login."
}
