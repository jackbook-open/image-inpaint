param(
    [switch]$NoIopaint,
    [switch]$SkipSmoke,
    [string]$RuntimeDir,
    [string]$PythonCommand = "python"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Invoke-Native {
    param(
        [string]$Description,
        [string]$FilePath,
        [string[]]$Arguments
    )

    Write-Host "==> $Description"
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Remove-DeepDirectory {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }
    $EmptyDir = Join-Path $env:TEMP "image-inpaint-empty-build"
    if (Test-Path $EmptyDir) {
        Remove-Item -Recurse -Force $EmptyDir
    }
    New-Item -ItemType Directory -Force -Path $EmptyDir | Out-Null
    & robocopy $EmptyDir $Path /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to clear build folder. Robocopy exit code: $LASTEXITCODE"
    }
    $global:LASTEXITCODE = 0
    Remove-Item -Recurse -Force $Path
    Remove-Item -Recurse -Force $EmptyDir
}

function Copy-DirectoryMirror {
    param(
        [string]$Source,
        [string]$Destination
    )

    Write-Host "==> Copy runtime"
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    & robocopy $Source $Destination /MIR /R:2 /W:2 /NFL /NDL /NJH /NP
    if ($LASTEXITCODE -gt 7) {
        throw "Runtime copy failed. Robocopy exit code: $LASTEXITCODE"
    }
    $global:LASTEXITCODE = 0
}

function New-ZipFromDirectory {
    param(
        [string]$SourceDirectory,
        [string]$ZipPath
    )

    Write-Host "==> Create release zip"
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath
    }
    [System.IO.Compression.ZipFile]::CreateFromDirectory(
        (Resolve-Path $SourceDirectory).Path,
        $ZipPath,
        [System.IO.Compression.CompressionLevel]::Optimal,
        $true
    )
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Invoke-Native "Create virtual environment" $PythonCommand @("-m", "venv", ".venv")
}

$Python = (Resolve-Path ".venv\Scripts\python.exe").Path
Invoke-Native "Upgrade pip" $Python @("-m", "pip", "install", "--upgrade", "pip")

$InstallExtras = if ($NoIopaint -or $RuntimeDir) {
    ".[desktop]"
} else {
    ".[desktop,iopaint]"
}

Invoke-Native "Install package dependencies" $Python @("-m", "pip", "install", "-e", $InstallExtras)
Invoke-Native "Build PyInstaller package" $Python @("-m", "PyInstaller", "--noconfirm", "packaging\pyinstaller-image-inpaint.spec")

$Exe = (Resolve-Path "dist\ImageInpaint\ImageInpaint.exe").Path
$SmokeExe = (Resolve-Path "dist\ImageInpaint\ImageInpaintSmoke.exe").Path
$WindowsInstallerDir = Join-Path $ProjectRoot "packaging\windows"
Copy-Item -Path (Join-Path $WindowsInstallerDir "*") -Destination "dist\ImageInpaint" -Recurse -Force

$PackagedRuntimeDir = Join-Path $ProjectRoot "dist\ImageInpaint\runtime"
if ($RuntimeDir) {
    $ResolvedRuntimeDir = (Resolve-Path $RuntimeDir).Path
    Remove-DeepDirectory $PackagedRuntimeDir
    Copy-DirectoryMirror $ResolvedRuntimeDir $PackagedRuntimeDir
    Write-Host "Bundled runtime: $ResolvedRuntimeDir -> $PackagedRuntimeDir"
}

if (-not $SkipSmoke) {
    if ($NoIopaint) {
        Invoke-Native "Packaged app smoke check" $SmokeExe @("--smoke-check")
    } else {
        Invoke-Native "Packaged app IOPaint runtime smoke check" $SmokeExe @("--smoke-check", "--require-iopaint")
    }
    $InstallSmokeArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "packaging\verify-windows-install-smoke.ps1")
    if (-not $NoIopaint) {
        $InstallSmokeArgs += @("-PackageDir", "dist\ImageInpaint", "-LaunchSmoke", "-RequireIopaint")
    }
    Invoke-Native "Windows install smoke check" "powershell.exe" $InstallSmokeArgs
}

$ReleaseDir = Join-Path $ProjectRoot "release"
New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
$ZipPath = Join-Path $ReleaseDir "ImageInpaint-Windows-x64.zip"
New-ZipFromDirectory "dist\ImageInpaint" $ZipPath
Invoke-Native "Write Windows checksum" $Python @("packaging\verify-checksum.py", "--write", $ZipPath)
$ZipSmokeArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "packaging\verify-windows-zip-smoke.ps1")
if (-not $NoIopaint) {
    $ZipSmokeArgs += "-RequireIopaint"
}
Invoke-Native "Windows zip smoke check" "powershell.exe" $ZipSmokeArgs

Write-Host ""
Write-Host "Build complete: dist\ImageInpaint"
Write-Host "Release package: $ZipPath"
Write-Host "Checksum: $ZipPath.sha256"
Write-Host "Run dist\ImageInpaint\ImageInpaint.exe to open the desktop app."
