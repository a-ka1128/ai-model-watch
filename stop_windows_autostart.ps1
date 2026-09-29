$ErrorActionPreference = "Continue"
$names = @(
    "AI Model Watch - Backend",
    "AI Model Watch - Frontend",
    "AI Model Watch - Weekly Pipeline",
    "AI Model Watch - Control Panel"
)
foreach ($name in $names) {
    Stop-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Output "Removed: $name"
}
