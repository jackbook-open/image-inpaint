param(
    [string]$SetupPath = "release\ImageInpaint-Setup-x64.exe",
    [string]$ScratchDir = "windows-installer-smoke",
    [switch]$RequireIopaint
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

function Remove-DeepDirectory {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }
    $EmptyDir = Join-Path $env:TEMP "image-inpaint-empty-installer-smoke"
    if (Test-Path $EmptyDir) {
        Remove-Item -Recurse -Force $EmptyDir
    }
    New-Item -ItemType Directory -Force -Path $EmptyDir | Out-Null
    & robocopy $EmptyDir $Path /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to clear installer smoke folder. Robocopy exit code: $LASTEXITCODE"
    }
    $global:LASTEXITCODE = 0
    Remove-Item -Recurse -Force $Path
    Remove-Item -Recurse -Force $EmptyDir
}

$ResolvedSetupPath = Resolve-Path $SetupPath
if (Test-Path "$ResolvedSetupPath.sha256") {
    & python "packaging\verify-checksum.py" $ResolvedSetupPath
    if ($LASTEXITCODE -ne 0) {
        throw "Windows installer checksum verification failed."
    }
}

$ScratchRoot = if ([System.IO.Path]::IsPathRooted($ScratchDir)) {
    $ScratchDir
} else {
    Join-Path "$env:SystemDrive\" $ScratchDir
}
$InstallDir = Join-Path $ScratchRoot "LocalAppData\ImageInpaint\app"
$InstallLog = Join-Path $ScratchRoot "install.log"
$UninstallLog = Join-Path $ScratchRoot "uninstall.log"

try {
    Remove-DeepDirectory $ScratchRoot
    New-Item -ItemType Directory -Force -Path $ScratchRoot | Out-Null

    $InstallProcess = Start-Process -FilePath $ResolvedSetupPath -ArgumentList @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/DIR=$InstallDir",
        "/LOG=$InstallLog"
    ) -Wait -PassThru
    if ($InstallProcess.ExitCode -ne 0) {
        throw "Windows installer silent install failed with exit code $($InstallProcess.ExitCode)."
    }

    $ExePath = Join-Path $InstallDir "ImageInpaint.exe"
    $SmokeExe = Join-Path $InstallDir "ImageInpaintSmoke.exe"
    $Readme = Join-Path $InstallDir "README-FIRST.txt"
    foreach ($Path in @($ExePath, $SmokeExe, $Readme)) {
        if (-not (Test-Path $Path)) {
            throw "Windows installer smoke missing expected path: $Path"
        }
    }

    $SmokeArgs = @("--smoke-check")
    if ($RequireIopaint) {
        $SmokeArgs += "--require-iopaint"
    }
    & $SmokeExe @SmokeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Windows installer installed app smoke failed."
    }

    $Uninstaller = Get-ChildItem -LiteralPath $InstallDir -Filter "unins*.exe" | Select-Object -First 1
    if (-not $Uninstaller) {
        throw "Windows installer smoke could not find the uninstaller."
    }
    $UninstallProcess = Start-Process -FilePath $Uninstaller.FullName -ArgumentList @(
        "/VERYSILENT",
        "/SUPPRESSMSGBOXES",
        "/NORESTART",
        "/LOG=$UninstallLog"
    ) -Wait -PassThru
    if ($UninstallProcess.ExitCode -ne 0) {
        throw "Windows installer silent uninstall failed with exit code $($UninstallProcess.ExitCode)."
    }
    if (Test-Path $ExePath) {
        throw "Windows installer silent uninstall left the main executable behind."
    }
} finally {
    Remove-DeepDirectory $ScratchRoot
}

Write-Host "Windows installer smoke passed."
