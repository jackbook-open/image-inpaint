param(
    [string]$AppPath = "dist\ImageInpaint\ImageInpaint.exe",
    [string]$OutDir = "release-smoke-output"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$ResolvedApp = Resolve-Path $AppPath
$AppDir = Split-Path -Parent $ResolvedApp
$SmokeApp = Join-Path $AppDir "ImageInpaintSmoke.exe"
if (-not (Test-Path $SmokeApp)) {
    $SmokeApp = $ResolvedApp
}

& $SmokeApp --smoke-check --require-iopaint
if ($LASTEXITCODE -ne 0) {
    throw "Packaged app runtime check failed."
}

if (Test-Path $OutDir) {
    Remove-Item -Recurse -Force $OutDir
}

& $SmokeApp `
    --process-smoke `
    --markdown "examples\document.md" `
    --out $OutDir `
    --mask-dir "examples\masks" `
    --model-dir ".model-cache"

if ($LASTEXITCODE -ne 0) {
    throw "Packaged app processing smoke failed."
}

$OutputMarkdown = Join-Path $OutDir "document.md"
$OutputImages = Join-Path $OutDir "images"
$OriginalBackup = Join-Path $OutDir "backups\original.md"
$BackupImages = Join-Path $OutDir "backups\images"
$RunLog = Join-Path $OutDir "logs\run.log"
if (-not (Test-Path $OutputMarkdown)) {
    throw "Missing output Markdown: $OutputMarkdown"
}
if (-not (Test-Path $OutputImages) -or -not (Get-ChildItem -Path $OutputImages -File | Select-Object -First 1)) {
    throw "Missing processed image output in: $OutputImages"
}
if (-not (Test-Path $OriginalBackup)) {
    throw "Missing original Markdown backup: $OriginalBackup"
}
if (-not (Test-Path $BackupImages) -or -not (Get-ChildItem -Path $BackupImages -File | Select-Object -First 1)) {
    throw "Missing source image backup in: $BackupImages"
}
if (-not (Test-Path $RunLog)) {
    throw "Missing run log: $RunLog"
}

Write-Host "Release verification passed."
Write-Host "Output Markdown: $OutputMarkdown"
Write-Host "Output images: $OutputImages"
Write-Host "Backups: $(Join-Path $OutDir 'backups')"
Write-Host "Run log: $RunLog"
