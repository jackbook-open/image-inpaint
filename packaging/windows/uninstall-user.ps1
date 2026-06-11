$ErrorActionPreference = "Stop"

$AppName = "Image Inpaint"
$AppDirName = "ImageInpaint"
$LocalAppData = if ($env:IMAGE_INPAINT_INSTALL_LOCALAPPDATA) { $env:IMAGE_INPAINT_INSTALL_LOCALAPPDATA } else { $env:LOCALAPPDATA }
$DesktopDir = if ($env:IMAGE_INPAINT_INSTALL_DESKTOP) { $env:IMAGE_INPAINT_INSTALL_DESKTOP } else { [Environment]::GetFolderPath("Desktop") }
$ProgramsDir = if ($env:IMAGE_INPAINT_INSTALL_PROGRAMS) { $env:IMAGE_INPAINT_INSTALL_PROGRAMS } else { [Environment]::GetFolderPath("Programs") }
$RegistryRoot = if ($env:IMAGE_INPAINT_INSTALL_REGISTRY_ROOT) { $env:IMAGE_INPAINT_INSTALL_REGISTRY_ROOT } else { "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" }
$InstallRoot = Join-Path $LocalAppData $AppDirName
$InstallDir = Join-Path $InstallRoot "app"
$DesktopShortcut = Join-Path $DesktopDir "$AppName.lnk"
$StartMenuDir = Join-Path $ProgramsDir $AppName
$RegistryPath = Join-Path $RegistryRoot $AppDirName

if (Test-Path $DesktopShortcut) {
    Remove-Item -Force $DesktopShortcut
}
if (Test-Path $StartMenuDir) {
    Remove-Item -Recurse -Force $StartMenuDir
}
if (Test-Path $InstallDir) {
    $EmptyDir = Join-Path $env:TEMP "image-inpaint-empty-uninstall"
    if (Test-Path $EmptyDir) {
        Remove-Item -Recurse -Force $EmptyDir
    }
    New-Item -ItemType Directory -Force -Path $EmptyDir | Out-Null
    & robocopy $EmptyDir $InstallDir /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to clear app install folder. Robocopy exit code: $LASTEXITCODE"
    }
    $global:LASTEXITCODE = 0
    Remove-Item -Recurse -Force $InstallDir
    Remove-Item -Recurse -Force $EmptyDir
}
if (Test-Path $RegistryPath) {
    Remove-Item -Recurse -Force $RegistryPath
}

Write-Host "$AppName was removed from this user account."
Write-Host "User outputs and model cache are kept under your normal user folders."
