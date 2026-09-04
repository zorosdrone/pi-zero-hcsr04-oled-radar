[CmdletBinding()]
param(
    [string]$Repository = "zorosdrone/pi-zero-hcsr04-oled-radar",
    [string]$Tag = "v1.0.0-radar-demo",
    [switch]$Prerelease
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$mediaDir = Join-Path $projectRoot "media"
$notesFile = Join-Path $mediaDir "release-notes-v1.0.0-radar-demo.md"
$assets = @(
    (Join-Path $mediaDir "radar-sweep-oled-demo-v1.0.0.mov"),
    (Join-Path $mediaDir "radar-oled-display-demo-v1.0.0.mov")
)

foreach ($asset in $assets + $notesFile) {
    if (-not (Test-Path -LiteralPath $asset -PathType Leaf)) {
        throw "Release file not found: $asset"
    }
}

$releaseArgs = @(
    "release", "create", $Tag,
    "--repo", $Repository,
    "--title", "HC-SR04 OLED Radar Demo v1.0.0",
    "--notes-file", $notesFile
)
if ($Prerelease) {
    $releaseArgs += "--prerelease"
}
$releaseArgs += $assets

& gh @releaseArgs
if ($LASTEXITCODE -ne 0) {
    throw "GitHub Release creation failed."
}
