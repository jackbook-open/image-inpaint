$ErrorActionPreference = "Stop"

$AppName = "Image Inpaint"
$AppDirName = "ImageInpaint"
$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalAppData = if ($env:IMAGE_INPAINT_INSTALL_LOCALAPPDATA) { $env:IMAGE_INPAINT_INSTALL_LOCALAPPDATA } else { $env:LOCALAPPDATA }
$DesktopDir = if ($env:IMAGE_INPAINT_INSTALL_DESKTOP) { $env:IMAGE_INPAINT_INSTALL_DESKTOP } else { [Environment]::GetFolderPath("Desktop") }
$ProgramsDir = if ($env:IMAGE_INPAINT_INSTALL_PROGRAMS) { $env:IMAGE_INPAINT_INSTALL_PROGRAMS } else { [Environment]::GetFolderPath("Programs") }
$RegistryRoot = if ($env:IMAGE_INPAINT_INSTALL_REGISTRY_ROOT) { $env:IMAGE_INPAINT_INSTALL_REGISTRY_ROOT } else { "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall" }
$InstallRoot = Join-Path $LocalAppData $AppDirName
$InstallDir = Join-Path $InstallRoot "app"
$ExePath = Join-Path $InstallDir "ImageInpaint.exe"
$UninstallScript = Join-Path $InstallRoot "uninstall-user.ps1"
$DesktopShortcut = Join-Path $DesktopDir "$AppName.lnk"
$StartMenuDir = Join-Path $ProgramsDir $AppName
$StartMenuShortcut = Join-Path $StartMenuDir "$AppName.lnk"
$UninstallShortcut = Join-Path $StartMenuDir "Uninstall $AppName.lnk"
$RegistryPath = Join-Path $RegistryRoot $AppDirName

if (-not (Test-Path (Join-Path $SourceDir "ImageInpaint.exe"))) {
    throw "ImageInpaint.exe was not found next to this installer. Please run the installer from the extracted package folder."
}

if (Test-Path $InstallDir) {
    Remove-Item -Recurse -Force $InstallDir
}
New-Item -ItemType Directory -Force -Path $InstallDir, $StartMenuDir, $DesktopDir | Out-Null

$ExcludedFiles = @("install-user.ps1", "uninstall-user.ps1", "Install Image Inpaint.cmd", "Uninstall Image Inpaint.cmd", "README-FIRST.txt")
$RoboCopyArgs = @(
    $SourceDir,
    $InstallDir,
    "/E",
    "/NFL",
    "/NDL",
    "/NJH",
    "/NJS",
    "/NP",
    "/XF"
) + $ExcludedFiles
& robocopy @RoboCopyArgs | Out-Null
if ($LASTEXITCODE -gt 7) {
    throw "Failed to copy app files into the install folder. Robocopy exit code: $LASTEXITCODE"
}
$global:LASTEXITCODE = 0

Copy-Item -LiteralPath (Join-Path $SourceDir "uninstall-user.ps1") -Destination $UninstallScript -Force

$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($DesktopShortcut)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "Open Image Inpaint"
$Shortcut.Save()

$Shortcut = $Shell.CreateShortcut($StartMenuShortcut)
$Shortcut.TargetPath = $ExePath
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "Open Image Inpaint"
$Shortcut.Save()

$Shortcut = $Shell.CreateShortcut($UninstallShortcut)
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$UninstallScript`""
$Shortcut.WorkingDirectory = $InstallRoot
$Shortcut.Description = "Uninstall Image Inpaint"
$Shortcut.Save()

New-Item -Path $RegistryPath -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "DisplayName" -Value $AppName -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "DisplayVersion" -Value "0.1.0" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "Publisher" -Value "image-inpaint contributors" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "InstallLocation" -Value $InstallDir -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "DisplayIcon" -Value $ExePath -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "UninstallString" -Value "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$UninstallScript`"" -PropertyType String -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "NoModify" -Value 1 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $RegistryPath -Name "NoRepair" -Value 1 -PropertyType DWord -Force | Out-Null

Write-Host "$AppName installed to: $InstallDir"
Write-Host "Desktop shortcut: $DesktopShortcut"
Write-Host "Start menu folder: $StartMenuDir"
