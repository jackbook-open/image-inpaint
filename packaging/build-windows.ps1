param(
    [switch]$NoIopaint,
    [switch]$Installer,
    [switch]$SkipSmoke,
    [string]$RuntimeDir,
    [string]$InnoSetupCompiler = "",
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
        [string]$Destination,
        [string]$Description = "Copy directory"
    )

    Write-Host "==> $Description"
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

function Resolve-InnoSetupCompiler {
    param([string]$PreferredPath)

    $Candidates = @()
    if ($PreferredPath) {
        $Candidates += $PreferredPath
    }
    $Command = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if ($Command) {
        $Candidates += $Command.Source
    }
    $Candidates += @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )

    foreach ($Candidate in $Candidates) {
        if ($Candidate -and (Test-Path $Candidate)) {
            return (Resolve-Path $Candidate).Path
        }
    }
    throw "Inno Setup compiler was not found. Install Inno Setup 6 or pass -InnoSetupCompiler C:\path\to\ISCC.exe."
}

function Get-ProjectVersion {
    $VersionLine = Select-String -Path "pyproject.toml" -Pattern '^version\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $VersionLine) {
        return "0.1.0"
    }
    return $VersionLine.Matches[0].Groups[1].Value
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
Get-ChildItem -LiteralPath $WindowsInstallerDir |
    Where-Object { $_.Extension -ne ".iss" } |
    Copy-Item -Destination "dist\ImageInpaint" -Recurse -Force

$PackagedRuntimeDir = Join-Path $ProjectRoot "dist\ImageInpaint\runtime"
if ($RuntimeDir) {
    $ResolvedRuntimeDir = (Resolve-Path $RuntimeDir).Path
    Remove-DeepDirectory $PackagedRuntimeDir
    Copy-DirectoryMirror $ResolvedRuntimeDir $PackagedRuntimeDir "Copy runtime"
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

if ($Installer) {
    $SetupPath = Join-Path $ReleaseDir "ImageInpaint-Setup-x64.exe"
    $InnoCompiler = Resolve-InnoSetupCompiler $InnoSetupCompiler
    $AppVersion = Get-ProjectVersion
    $InstallerSourceDir = Join-Path $env:TEMP "image-inpaint-inno-source"
    if (Test-Path $SetupPath) {
        Remove-Item $SetupPath
    }
    try {
        Remove-DeepDirectory $InstallerSourceDir
        Copy-DirectoryMirror "dist\ImageInpaint" $InstallerSourceDir "Stage installer source"
        Get-ChildItem -LiteralPath $InstallerSourceDir -Filter "*.iss" -ErrorAction SilentlyContinue |
            Remove-Item -Force
        Invoke-Native "Build Windows installer" $InnoCompiler @(
            "/DAppVersion=$AppVersion",
            "/DSourceDir=`"$InstallerSourceDir`"",
            "/DOutputDir=`"$ReleaseDir`"",
            "packaging\windows\ImageInpaint.iss"
        )
    } finally {
        Remove-DeepDirectory $InstallerSourceDir
    }
    Invoke-Native "Write Windows installer checksum" $Python @("packaging\verify-checksum.py", "--write", $SetupPath)
    if (-not $SkipSmoke) {
        $InstallerSmokeArgs = @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "packaging\verify-windows-installer-smoke.ps1",
            "-SetupPath",
            $SetupPath
        )
        if (-not $NoIopaint) {
            $InstallerSmokeArgs += "-RequireIopaint"
        }
        Invoke-Native "Windows installer smoke check" "powershell.exe" $InstallerSmokeArgs
    }
}

Write-Host ""
Write-Host "Build complete: dist\ImageInpaint"
Write-Host "Release package: $ZipPath"
Write-Host "Checksum: $ZipPath.sha256"
if ($Installer) {
    Write-Host "Installer: $SetupPath"
    Write-Host "Installer checksum: $SetupPath.sha256"
}
Write-Host "Run dist\ImageInpaint\ImageInpaint.exe to open the desktop app."
