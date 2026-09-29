param()
$ErrorActionPreference = 'Stop'
$projectDir = $PSScriptRoot
$exePath = Join-Path $projectDir 'dist\AI_Model_Watch_Control_Panel.exe'
$assetDir = Join-Path $projectDir 'assets'
$iconPath = Join-Path $assetDir 'ai-model-watch-desktop.ico'
$previewPath = Join-Path $assetDir 'ai-model-watch-desktop.png'
$desktopDir = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktopDir 'AI Model Watch.lnk'
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) { throw "Missing control panel: $exePath" }
if (Test-Path -LiteralPath $shortcutPath) { throw "Shortcut already exists: $shortcutPath" }
New-Item -ItemType Directory -Path $assetDir -Force | Out-Null
Add-Type -AssemblyName System.Drawing

function New-AppBitmap([int]$size) {
    $bitmap = New-Object System.Drawing.Bitmap($size, $size)
    $g = [System.Drawing.Graphics]::FromImage($bitmap)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.Clear([System.Drawing.Color]::Transparent)
    $g.ScaleTransform(($size / 256.0), ($size / 256.0))
    $background = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml('#28654F'))
    $paper = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml('#FFFEF5'))
    $gold = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml('#E9BF64'), 13)
    $lines = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml('#28654F'), 10)
    $gold.StartCap = $gold.EndCap = $lines.StartCap = $lines.EndCap = [System.Drawing.Drawing2D.LineCap]::Round
    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $path.AddArc(8, 8, 64, 64, 180, 90)
    $path.AddArc(184, 8, 64, 64, 270, 90)
    $path.AddArc(184, 184, 64, 64, 0, 90)
    $path.AddArc(8, 184, 64, 64, 90, 90)
    $path.CloseFigure()
    $g.FillPath($background, $path)
    $g.FillRectangle($paper, 58, 46, 126, 155)
    $g.DrawLine($lines, 80, 77, 158, 77)
    $g.DrawLine($lines, 80, 106, 148, 106)
    $g.DrawLine($lines, 80, 135, 117, 135)
    $g.FillEllipse($background, 122, 128, 79, 79)
    $g.DrawEllipse($gold, 128, 134, 63, 63)
    $g.DrawLine($gold, 184, 191, 210, 217)
    $path.Dispose(); $background.Dispose(); $paper.Dispose(); $gold.Dispose(); $lines.Dispose(); $g.Dispose()
    return ,$bitmap
}

$sizes = @(16, 24, 32, 48, 64, 128, 256)
$images = @()
foreach ($size in $sizes) {
    $bitmap = New-AppBitmap $size
    $stream = New-Object System.IO.MemoryStream
    $bitmap.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
    $images += ,$stream.ToArray()
    if ($size -eq 256) { $bitmap.Save($previewPath, [System.Drawing.Imaging.ImageFormat]::Png) }
    $stream.Dispose(); $bitmap.Dispose()
}
$file = [System.IO.File]::Create($iconPath)
$writer = New-Object System.IO.BinaryWriter($file)
try {
    $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]$sizes.Count)
    $offset = 6 + 16 * $sizes.Count
    for ($index = 0; $index -lt $sizes.Count; $index++) {
        $dimension = if ($sizes[$index] -eq 256) { 0 } else { $sizes[$index] }
        $writer.Write([byte]$dimension); $writer.Write([byte]$dimension)
        $writer.Write([byte]0); $writer.Write([byte]0)
        $writer.Write([uint16]1); $writer.Write([uint16]32)
        $writer.Write([uint32]$images[$index].Length); $writer.Write([uint32]$offset)
        $offset += $images[$index].Length
    }
    foreach ($bytes in $images) { $writer.Write([byte[]]$bytes) }
} finally { $writer.Dispose(); $file.Dispose() }

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = $projectDir
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = 'AI Model Watch Control Panel'
$shortcut.WindowStyle = 1
$shortcut.Save()
$verified = $shell.CreateShortcut($shortcutPath)
if ($verified.TargetPath -ne $exePath -or $verified.IconLocation -ne "$iconPath,0") { throw 'Shortcut verification failed' }
Write-Output "Shortcut: $shortcutPath"
Write-Output "Target: $($verified.TargetPath)"
Write-Output "Icon: $($verified.IconLocation)"
