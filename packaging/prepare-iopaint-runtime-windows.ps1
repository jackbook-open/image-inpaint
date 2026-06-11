param(
    [string]$RuntimeDir = "iopaint-runtime",
    [string]$PythonCommand = "python",
    [string]$TorchIndexUrl = "",
    [switch]$Force
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

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Assert-CompatiblePython {
    param([string]$PythonExecutable)

    $ProbePath = Join-Path ([System.IO.Path]::GetTempPath()) "image-inpaint-python-preflight.py"
    @'
import platform
import struct
import sys

major, minor = sys.version_info[:2]
bits = struct.calcsize("P") * 8
print(f"Python {major}.{minor}.{sys.version_info.micro} ({bits}-bit) at {sys.executable}")
if bits != 64:
    raise SystemExit("IOPaint/PyTorch runtime builds require 64-bit Python.")
if (major, minor) < (3, 10) or (major, minor) >= (3, 13):
    raise SystemExit("Use Python 3.10, 3.11, or 3.12 for IOPaint/PyTorch runtime builds.")
'@ | Set-Content -Path $ProbePath -Encoding UTF8
    try {
        & $PythonExecutable $ProbePath
        if ($LASTEXITCODE -ne 0) {
            throw "Python runtime preflight failed. Install 64-bit Python 3.10, 3.11, or 3.12 and pass it with -PythonCommand."
        }
    } finally {
        Remove-Item -LiteralPath $ProbePath -ErrorAction SilentlyContinue
    }
}

function Assert-RuntimeImports {
    param([string]$PythonExecutable)

    $ProbePath = Join-Path ([System.IO.Path]::GetTempPath()) "image-inpaint-runtime-imports.py"
    @'
import importlib.metadata as metadata
import torch

print("torch:", metadata.version("torch"))
print("iopaint:", metadata.version("iopaint"))
'@ | Set-Content -Path $ProbePath -Encoding UTF8
    try {
        & $PythonExecutable $ProbePath
        if ($LASTEXITCODE -ne 0) {
            throw "Runtime import check failed. Review the pip output above for IOPaint/PyTorch wheel errors."
        }
    } finally {
        Remove-Item -LiteralPath $ProbePath -ErrorAction SilentlyContinue
    }
}

$ResolvedRuntimeDir = Join-Path $ProjectRoot $RuntimeDir
if (Test-Path $ResolvedRuntimeDir) {
    if (-not $Force) {
        throw "Runtime directory already exists: $ResolvedRuntimeDir. Re-run with -Force to replace it."
    }
    Remove-Item -Recurse -Force $ResolvedRuntimeDir
}

Assert-CompatiblePython $PythonCommand
Invoke-Native "Create IOPaint runtime" $PythonCommand @("-m", "venv", $ResolvedRuntimeDir)
$RuntimePython = Join-Path $ResolvedRuntimeDir "Scripts\python.exe"
Assert-CompatiblePython $RuntimePython
Invoke-Native "Upgrade runtime pip" $RuntimePython @("-m", "pip", "install", "--upgrade", "pip")

if ($TorchIndexUrl) {
    Invoke-Native "Install runtime IOPaint" $RuntimePython @("-m", "pip", "install", "iopaint>=1.5.0", "--extra-index-url", $TorchIndexUrl)
} else {
    Invoke-Native "Install runtime IOPaint" $RuntimePython @("-m", "pip", "install", "iopaint>=1.5.0")
}

Assert-RuntimeImports $RuntimePython

$Wrapper = Join-Path $ResolvedRuntimeDir "iopaint.cmd"
$WrapperText = @"
@echo off
set "RUNTIME_DIR=%~dp0"
"%RUNTIME_DIR%Scripts\python.exe" -m iopaint %*
"@
Set-Content -Path $Wrapper -Value $WrapperText -Encoding ASCII

Invoke-Native "Check runtime IOPaint command" $Wrapper @("--help")

Write-Host ""
Write-Host "IOPaint runtime prepared: $ResolvedRuntimeDir"
Write-Host "Build with: .\packaging\build-windows.ps1 -RuntimeDir `"$ResolvedRuntimeDir`""
