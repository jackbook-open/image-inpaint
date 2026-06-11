param(
    [string]$AppPath = "dist\ImageInpaint\ImageInpaint.exe",
    [string]$RuntimeDir = "fake-iopaint-runtime",
    [string]$OutDir = "packaged-process-smoke-output"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

$ResolvedApp = Resolve-Path $AppPath
$AppDir = Split-Path -Parent $ResolvedApp
$SmokeApp = Join-Path $AppDir "ImageInpaintSmoke.exe"
if (-not (Test-Path $SmokeApp)) {
    $SmokeApp = $ResolvedApp
}

if (-not (Test-Path $RuntimeDir)) {
    & (Join-Path $PSScriptRoot "make-fake-iopaint-runtime.ps1") -RuntimeDir $RuntimeDir
}

if (Test-Path $OutDir) {
    Remove-Item -Recurse -Force $OutDir
}

$env:IMAGE_INPAINT_RUNTIME_DIR = (Resolve-Path $RuntimeDir).Path
try {
    & $SmokeApp `
        --process-smoke `
        --markdown "examples\document.md" `
        --out $OutDir `
        --mask-dir "examples\masks" `
        --model-dir ".model-cache"
    if ($LASTEXITCODE -ne 0) {
        throw "Packaged process smoke failed."
    }
} finally {
    Remove-Item Env:\IMAGE_INPAINT_RUNTIME_DIR -ErrorAction SilentlyContinue
}

Remove-Item -Recurse -Force $OutDir
Write-Host "Packaged process smoke passed."
