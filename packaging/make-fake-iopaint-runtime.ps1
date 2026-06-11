param(
    [string]$RuntimeDir = "fake-iopaint-runtime"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$ResolvedRuntimeDir = Join-Path $ProjectRoot $RuntimeDir
if (Test-Path $ResolvedRuntimeDir) {
    Remove-Item -Recurse -Force $ResolvedRuntimeDir
}
New-Item -ItemType Directory -Force -Path $ResolvedRuntimeDir | Out-Null

@'
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

if (-not ($Args -contains "run")) {
    exit 3
}

$ImageDir = $null
$OutputDir = $null
foreach ($Arg in $Args) {
    if ($Arg.StartsWith("--image=")) {
        $ImageDir = $Arg.Substring(8)
    }
    if ($Arg.StartsWith("--output=")) {
        $OutputDir = $Arg.Substring(9)
    }
}

if (-not $ImageDir -or -not $OutputDir) {
    exit 4
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
Get-ChildItem -Path $ImageDir -File | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $OutputDir $_.Name)
}
'@ | Set-Content -Path (Join-Path $ResolvedRuntimeDir "fake-iopaint.ps1") -Encoding UTF8

@'
@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0fake-iopaint.ps1" %*
'@ | Set-Content -Path (Join-Path $ResolvedRuntimeDir "iopaint.cmd") -Encoding ASCII

Write-Host "Fake IOPaint runtime prepared: $ResolvedRuntimeDir"
