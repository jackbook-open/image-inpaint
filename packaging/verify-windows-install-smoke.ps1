param(
    [string]$PackageDir = "",
    [string]$ScratchDir = "windows-install-smoke",
    [switch]$LaunchSmoke,
    [switch]$RequireIopaint
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$ScratchRoot = Join-Path $ProjectRoot $ScratchDir
$PackageFixtureDir = Join-Path $ScratchRoot "Package"
$LocalAppData = Join-Path $ScratchRoot "LocalAppData"
$DesktopDir = Join-Path $ScratchRoot "Desktop"
$ProgramsDir = Join-Path $ScratchRoot "Programs"
$RegistryRoot = "HKCU:\Software\ImageInpaintInstallSmoke\Uninstall"

function Remove-DeepDirectory {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return
    }
    $EmptyDir = Join-Path $env:TEMP "image-inpaint-empty-smoke"
    if (Test-Path $EmptyDir) {
        Remove-Item -Recurse -Force $EmptyDir
    }
    New-Item -ItemType Directory -Force -Path $EmptyDir | Out-Null
    & robocopy $EmptyDir $Path /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to clear smoke folder. Robocopy exit code: $LASTEXITCODE"
    }
    $global:LASTEXITCODE = 0
    Remove-Item -Recurse -Force $Path
    Remove-Item -Recurse -Force $EmptyDir
}

Remove-DeepDirectory $ScratchRoot
if (Test-Path "HKCU:\Software\ImageInpaintInstallSmoke") {
    Remove-Item -Recurse -Force "HKCU:\Software\ImageInpaintInstallSmoke"
}
New-Item -ItemType Directory -Force -Path $LocalAppData, $DesktopDir, $ProgramsDir, $PackageFixtureDir | Out-Null

if ($PackageDir) {
    $ResolvedPackageDir = (Resolve-Path $PackageDir).Path
} else {
    $ResolvedPackageDir = $PackageFixtureDir
    Copy-Item -LiteralPath "packaging\windows\install-user.ps1" -Destination $ResolvedPackageDir -Force
    Copy-Item -LiteralPath "packaging\windows\uninstall-user.ps1" -Destination $ResolvedPackageDir -Force
    Copy-Item -LiteralPath "packaging\windows\README-FIRST.txt" -Destination $ResolvedPackageDir -Force
    Copy-Item -LiteralPath "packaging\windows\Install Image Inpaint.cmd" -Destination $ResolvedPackageDir -Force
    Copy-Item -LiteralPath "packaging\windows\Uninstall Image Inpaint.cmd" -Destination $ResolvedPackageDir -Force
    Set-Content -Path (Join-Path $ResolvedPackageDir "ImageInpaint.exe") -Value "install smoke executable placeholder" -Encoding ASCII
    $DeepDir = Join-Path $ResolvedPackageDir "runtime\Lib\site-packages\controlnet_aux\normalbae\nets\submodules\efficientnet_repo\geffnet\activations\__pycache__"
    New-Item -ItemType Directory -Force -Path $DeepDir | Out-Null
    Set-Content -Path (Join-Path $DeepDir "activations.cpython-312.pyc") -Value "deep path smoke file" -Encoding ASCII
}

$env:IMAGE_INPAINT_INSTALL_LOCALAPPDATA = $LocalAppData
$env:IMAGE_INPAINT_INSTALL_DESKTOP = $DesktopDir
$env:IMAGE_INPAINT_INSTALL_PROGRAMS = $ProgramsDir
$env:IMAGE_INPAINT_INSTALL_REGISTRY_ROOT = $RegistryRoot

try {
    & (Join-Path $ResolvedPackageDir "install-user.ps1")

    $InstallDir = Join-Path $LocalAppData "ImageInpaint\app"
    $ExePath = Join-Path $InstallDir "ImageInpaint.exe"
    $SmokeExePath = Join-Path $InstallDir "ImageInpaintSmoke.exe"
    $DesktopShortcut = Join-Path $DesktopDir "Image Inpaint.lnk"
    $StartMenuShortcut = Join-Path $ProgramsDir "Image Inpaint\Image Inpaint.lnk"
    $UninstallShortcut = Join-Path $ProgramsDir "Image Inpaint\Uninstall Image Inpaint.lnk"
    $RegistryPath = Join-Path $RegistryRoot "ImageInpaint"

    foreach ($Path in @($InstallDir, $ExePath, $DesktopShortcut, $StartMenuShortcut, $UninstallShortcut, $RegistryPath)) {
        if (-not (Test-Path $Path)) {
            throw "Windows install smoke missing expected path: $Path"
        }
    }

    $DisplayName = (Get-ItemProperty -Path $RegistryPath -Name DisplayName).DisplayName
    if ($DisplayName -ne "Image Inpaint") {
        throw "Windows install smoke found wrong DisplayName: $DisplayName"
    }

    if ($LaunchSmoke) {
        if (-not (Test-Path $SmokeExePath)) {
            throw "Windows install smoke missing launch smoke executable: $SmokeExePath"
        }
        $SmokeArgs = @("--smoke-check")
        if ($RequireIopaint) {
            $SmokeArgs += "--require-iopaint"
        }
        & $SmokeExePath @SmokeArgs
        if ($LASTEXITCODE -ne 0) {
            throw "Windows installed app launch smoke failed."
        }
    }

    & (Join-Path $ResolvedPackageDir "uninstall-user.ps1")

    foreach ($Path in @($InstallDir, $DesktopShortcut, $StartMenuShortcut, $UninstallShortcut, $RegistryPath)) {
        if (Test-Path $Path) {
            throw "Windows install smoke left path after uninstall: $Path"
        }
    }
} finally {
    Remove-Item Env:\IMAGE_INPAINT_INSTALL_LOCALAPPDATA -ErrorAction SilentlyContinue
    Remove-Item Env:\IMAGE_INPAINT_INSTALL_DESKTOP -ErrorAction SilentlyContinue
    Remove-Item Env:\IMAGE_INPAINT_INSTALL_PROGRAMS -ErrorAction SilentlyContinue
    Remove-Item Env:\IMAGE_INPAINT_INSTALL_REGISTRY_ROOT -ErrorAction SilentlyContinue
    if (Test-Path "HKCU:\Software\ImageInpaintInstallSmoke") {
        Remove-Item -Recurse -Force "HKCU:\Software\ImageInpaintInstallSmoke"
    }
    Remove-DeepDirectory $ScratchRoot
}

Write-Host "Windows install smoke passed."
