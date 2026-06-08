param(
    [switch]$Help,
    [switch]$CheckOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Resolve-Path -Path (Join-Path $ProjectRoot ".venv\Scripts\python.exe") -ErrorAction SilentlyContinue

function Select-Python {
    if ($VenvPython) {
        return $VenvPython.Path
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    return $null
}

function Show-Usage {
    Write-Host "image-inpaint launcher"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\start.ps1            Start the GUI"
    Write-Host "  .\start.ps1 -CheckOnly Check Python and dependencies"
    Write-Host "  .\start.ps1 -Help      Show this help"
    Write-Host ""
    Write-Host "Python lookup order:"
    Write-Host "  1. .\.venv\Scripts\python.exe"
    Write-Host "  2. python on PATH"
}

if ($Help) {
    Show-Usage
    exit 0
}

$Python = Select-Python
if (-not $Python) {
    Write-Error "Python was not found. Create a venv first or install Python, then run .\start.ps1 again."
}

$env:PYTHONPATH = (Join-Path $ProjectRoot "src")
Set-Location $ProjectRoot

Write-Host "Using Python: $Python"

& $Python -c "import tkinter; import yaml; import PIL; import md_image_inpaint.gui; print('Dependency check OK')"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Dependency check failed. Try one of these:"
    Write-Host "  python -m pip install -e ."
    Write-Host "  python -m pip install -e .[iopaint]"
    exit $LASTEXITCODE
}

if ($CheckOnly) {
    exit 0
}

& $Python -m md_image_inpaint --gui
exit $LASTEXITCODE
