param(
    [switch]$Real
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$DefaultModelDir = Join-Path $ProjectRoot "..\.model-cache"
$VenvPythonPath = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPythonPath) {
    $Python = (Resolve-Path $VenvPythonPath).Path
} else {
    $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $PythonCommand) {
        Write-Error "Python was not found."
    }
    $Python = $PythonCommand.Source
}

$env:PYTHONPATH = (Join-Path $ProjectRoot "src")
Set-Location $ProjectRoot

if ($Real) {
    $IopaintCommand = Get-Command iopaint -ErrorAction SilentlyContinue
    if (-not $IopaintCommand) {
        Write-Error "IOPaint was not found on PATH. Install with: python -m pip install -e .[iopaint]"
    }
    & $Python -m md_image_inpaint examples\document.md --out output --mask-dir examples\masks --engine iopaint --model lama --device cpu --model-dir $DefaultModelDir --iopaint-cmd $IopaintCommand.Source --verbose
    exit $LASTEXITCODE
}

& $Python -m md_image_inpaint examples\document.md --out output --mask-dir examples\masks --dry-run --verbose
exit $LASTEXITCODE
