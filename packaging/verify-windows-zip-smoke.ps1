param(
    [string]$ZipPath = "release\ImageInpaint-Windows-x64.zip",
    [string]$ScratchDir = "",
    [switch]$FullExtract,
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
    $EmptyDir = Join-Path $env:TEMP "image-inpaint-empty-zip-smoke"
    if (Test-Path $EmptyDir) {
        Remove-Item -Recurse -Force $EmptyDir
    }
    New-Item -ItemType Directory -Force -Path $EmptyDir | Out-Null
    & robocopy $EmptyDir $Path /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
    if ($LASTEXITCODE -gt 7) {
        throw "Failed to clear zip smoke folder. Robocopy exit code: $LASTEXITCODE"
    }
    $global:LASTEXITCODE = 0
    Remove-Item -Recurse -Force $Path
    Remove-Item -Recurse -Force $EmptyDir
}

$ResolvedZipPath = Resolve-Path $ZipPath
& python "packaging\verify-checksum.py" $ResolvedZipPath
if ($LASTEXITCODE -ne 0) {
    throw "Windows zip checksum verification failed."
}
$ScratchRoot = if ($ScratchDir) {
    Join-Path $ProjectRoot $ScratchDir
} else {
    Join-Path $env:TEMP "image-inpaint-zip-smoke"
}
$ExtractDir = Join-Path $ScratchRoot "Extracted"

try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Archive = [System.IO.Compression.ZipFile]::OpenRead($ResolvedZipPath)
    try {
        $EntryNames = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
        foreach ($Entry in $Archive.Entries) {
            [void]$EntryNames.Add($Entry.FullName.Replace("/", "\"))
        }
        $ExpectedEntries = @(
            "ImageInpaint\ImageInpaint.exe",
            "ImageInpaint\ImageInpaintSmoke.exe",
            "ImageInpaint\install-user.ps1",
            "ImageInpaint\uninstall-user.ps1",
            "ImageInpaint\Install Image Inpaint.cmd",
            "ImageInpaint\Uninstall Image Inpaint.cmd",
            "ImageInpaint\README-FIRST.txt"
        )
        if ($RequireIopaint) {
            $ExpectedEntries += "ImageInpaint\runtime\iopaint.cmd"
        }
        foreach ($Path in $ExpectedEntries) {
            if (-not $EntryNames.Contains($Path)) {
                throw "Windows zip smoke missing expected entry: $Path"
            }
        }
    } finally {
        $Archive.Dispose()
    }

    if (-not $FullExtract) {
        Write-Host "Windows zip smoke passed."
        return
    }

    Remove-DeepDirectory $ScratchRoot
    New-Item -ItemType Directory -Force -Path $ExtractDir | Out-Null
    [System.IO.Compression.ZipFile]::ExtractToDirectory($ResolvedZipPath.ProviderPath, $ExtractDir)
    $PackageDir = Join-Path $ExtractDir "ImageInpaint"
    $ExePath = Join-Path $PackageDir "ImageInpaint.exe"
    $SmokeExe = Join-Path $PackageDir "ImageInpaintSmoke.exe"
    $Installer = Join-Path $PackageDir "install-user.ps1"
    $Readme = Join-Path $PackageDir "README-FIRST.txt"

    foreach ($Path in @($PackageDir, $ExePath, $SmokeExe, $Installer, $Readme)) {
        if (-not (Test-Path $Path)) {
            throw "Windows zip smoke missing expected path: $Path"
        }
    }

    $SmokeArgs = @("--smoke-check")
    if ($RequireIopaint) {
        $SmokeArgs += "--require-iopaint"
    }
    & $SmokeExe @SmokeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Windows zip smoke runtime check failed."
    }

    $InstallSmokeArgs = @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "packaging\verify-windows-install-smoke.ps1",
        "-PackageDir",
        $PackageDir,
        "-ScratchDir",
        "windows-zip-install-smoke",
        "-LaunchSmoke"
    )
    if ($RequireIopaint) {
        $InstallSmokeArgs += "-RequireIopaint"
    }
    & powershell.exe @InstallSmokeArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Windows zip install smoke failed."
    }
} finally {
    if ($FullExtract) {
        Remove-DeepDirectory $ScratchRoot
    }
}

Write-Host "Windows zip smoke passed."
