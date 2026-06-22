param(
    [string]$Version = "",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

if (-not $Version) {
    $Version = (python -c "from app.version import app_version; print(app_version())").Trim()
}

Write-Host "==> Scenaria build v$Version" -ForegroundColor Cyan

Write-Host "==> Install dependencies" -ForegroundColor Cyan
python -m pip install -r requirements.txt -r requirements-dev.txt --quiet
python -m playwright install chromium

if (-not $SkipTests) {
    Write-Host "==> Run tests" -ForegroundColor Cyan
    python -m pytest tests/ -q
}

Write-Host "==> Build exe (PyInstaller)" -ForegroundColor Cyan
python -m PyInstaller Scenaria.spec --noconfirm

$Dist = Join-Path $Root "dist\Scenaria"
$BrowsersTarget = Join-Path $Dist "browsers"
$PlaywrightLocal = Join-Path $env:LOCALAPPDATA "ms-playwright"

if (-not (Test-Path $PlaywrightLocal)) {
    throw "Playwright browsers not found at $PlaywrightLocal"
}

Write-Host "==> Copy Chromium into dist\browsers (without headless_shell)" -ForegroundColor Cyan
if (Test-Path $BrowsersTarget) {
    Remove-Item $BrowsersTarget -Recurse -Force
}
New-Item -ItemType Directory -Path $BrowsersTarget | Out-Null
Get-ChildItem $PlaywrightLocal -Directory | Where-Object {
    $_.Name -like "chromium-*" -or $_.Name -like "ffmpeg-*"
} | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $BrowsersTarget $_.Name) -Recurse -Force
}

New-Item -ItemType Directory -Path (Join-Path $Dist "data") -Force | Out-Null
$ExamplesSource = Join-Path $Root "examples"
if (Test-Path $ExamplesSource) {
    Write-Host "==> Copy examples into dist\examples" -ForegroundColor Cyan
    Copy-Item $ExamplesSource (Join-Path $Dist "examples") -Recurse -Force
}
$versionPath = Join-Path $Dist "version.txt"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($versionPath, $Version, $utf8NoBom)

function Get-FolderSizeMb {
    param([string]$Path)
    $bytes = (Get-ChildItem $Path -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
    if (-not $bytes) { return 0 }
    return [math]::Round($bytes / 1MB, 1)
}

function New-ReleaseZip {
    param(
        [string]$SourceDir,
        [string]$ZipPath,
        [string[]]$ExcludeTopLevel = @()
    )
    if (Test-Path $ZipPath) {
        Remove-Item $ZipPath -Force
    }
    $stage = Join-Path $env:TEMP ("shop-recorder-stage-" + [guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $stage | Out-Null
    try {
        Copy-Item $SourceDir (Join-Path $stage "Scenaria") -Recurse
        $target = Join-Path $stage "Scenaria"
        foreach ($name in $ExcludeTopLevel) {
            $item = Join-Path $target $name
            if (Test-Path $item) {
                Remove-Item $item -Recurse -Force
            }
        }
        Compress-Archive -Path (Join-Path $stage "Scenaria") -DestinationPath $ZipPath
    }
    finally {
        Remove-Item $stage -Recurse -Force -ErrorAction SilentlyContinue
    }
}

$PortableDir = Join-Path $Root "dist\Scenaria-Portable"
if (Test-Path $PortableDir) {
    Remove-Item $PortableDir -Recurse -Force
}
Copy-Item $Dist $PortableDir -Recurse

$DistRoot = Join-Path $Root "dist"
$FullZip = Join-Path $DistRoot "Scenaria-Portable.zip"
$UpdateZip = Join-Path $DistRoot "Scenaria-update.zip"
New-ReleaseZip -SourceDir $Dist -ZipPath $FullZip
New-ReleaseZip -SourceDir $Dist -ZipPath $UpdateZip -ExcludeTopLevel @("browsers", "data")

function Get-FileSha256 {
    param([string]$Path)
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
}

$Manifest = @{
    version = $Version
    published_at = (Get-Date).ToUniversalTime().ToString("o")
    assets = @{
        portable = @{
            name = "Scenaria-Portable.zip"
            size = (Get-Item $FullZip).Length
            sha256 = (Get-FileSha256 $FullZip)
        }
        update = @{
            name = "Scenaria-update.zip"
            size = (Get-Item $UpdateZip).Length
            sha256 = (Get-FileSha256 $UpdateZip)
        }
    }
}
$ManifestPath = Join-Path $DistRoot "latest.json"
$Manifest | ConvertTo-Json -Depth 6 | Set-Content -Path $ManifestPath -Encoding UTF8

$DistMb = Get-FolderSizeMb $PortableDir
$BrowsersMb = Get-FolderSizeMb (Join-Path $PortableDir "browsers")
$InternalMb = Get-FolderSizeMb (Join-Path $PortableDir "_internal")

Write-Host ""
Write-Host "Build complete (v$Version):" -ForegroundColor Green
Write-Host "  EXE:     $Dist\Scenaria.exe"
Write-Host "  Portable $PortableDir"
Write-Host "  Full ZIP $FullZip ($([math]::Round((Get-Item $FullZip).Length / 1MB, 1)) MB)"
Write-Host "  App ZIP  $UpdateZip ($([math]::Round((Get-Item $UpdateZip).Length / 1MB, 1)) MB, no browsers)"
Write-Host "  Manifest $ManifestPath"
Write-Host ""
Write-Host "Size breakdown:" -ForegroundColor Cyan
Write-Host "  Total:    $DistMb MB"
Write-Host "  browsers: $BrowsersMb MB"
Write-Host "  _internal: $InternalMb MB"
