[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$rootPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$distPath = Join-Path $rootPath 'dist'
New-Item -ItemType Directory -Force -Path $distPath | Out-Null
$stagePath = Join-Path $distPath ('package-' + [Guid]::NewGuid().ToString('N'))
$appPath = Join-Path $stagePath 'Tarkash Video Studio'
$zipPath = Join-Path $distPath 'Tarkash-Video-Studio.zip'

try {
    foreach ($required in @('app.py', 'launch.py', 'requirements.txt', 'Install.cmd', 'Launch.cmd', 'README.md', 'HOW-TO-USE.md', 'THIRD_PARTY_NOTICES.md', 'scripts\setup_voices.py', 'data\default-project.json')) {
        if (-not (Test-Path -LiteralPath (Join-Path $rootPath $required))) { throw "Cannot package: $required is missing." }
    }
    New-Item -ItemType Directory -Path $appPath | Out-Null
    Get-ChildItem -LiteralPath $rootPath -File -Filter '*.py' | Where-Object { $_.Name -ne 'seed_from_sources.py' } | Copy-Item -Destination $appPath
    foreach ($name in @('requirements.txt', 'Install.cmd', 'Launch.cmd', 'Stop.cmd', 'README.md', 'HOW-TO-USE.md', 'THIRD_PARTY_NOTICES.md', 'video_design.css', 'content_design.css', 'installer', 'static', 'templates', 'web')) {
        $sourcePath = Join-Path $rootPath $name
        if (Test-Path -LiteralPath $sourcePath) { Copy-Item -LiteralPath $sourcePath -Destination $appPath -Recurse }
    }
    $scriptsPath = Join-Path $appPath 'scripts'
    New-Item -ItemType Directory -Path $scriptsPath | Out-Null
    foreach ($script in @('speech.ps1', 'setup_voices.py')) {
        Copy-Item -LiteralPath (Join-Path $rootPath ('scripts\' + $script)) -Destination $scriptsPath
    }
    $sourceAssets = Join-Path $rootPath 'assets'
    if (Test-Path -LiteralPath $sourceAssets) {
        $assetPath = Join-Path $appPath 'assets'
        New-Item -ItemType Directory -Path $assetPath | Out-Null
        Get-ChildItem -LiteralPath $sourceAssets -Force |
            Where-Object { $_.Name -ne 'uploads' -and $_.Name -ne '__pycache__' } |
            Copy-Item -Destination $assetPath -Recurse
    }
    $dataPath = Join-Path $appPath 'data'
    New-Item -ItemType Directory -Path $dataPath | Out-Null
    Copy-Item -LiteralPath (Join-Path $rootPath 'data\default-project.json') -Destination $dataPath
    # A fresh stage is used on every run; do not copy original videos or local user data.
    Compress-Archive -LiteralPath $appPath -DestinationPath $zipPath -Force -CompressionLevel Optimal
    Write-Host "Created $zipPath"
    Write-Host 'Extract the ZIP before double-clicking Install.cmd. First setup needs internet.'
} finally {
    # Verify the fully resolved, unique stage remains inside this project's dist folder.
    $resolvedStage = [IO.Path]::GetFullPath($stagePath)
    $resolvedDist = [IO.Path]::GetFullPath($distPath).TrimEnd('\') + '\'
    if ($resolvedStage.StartsWith($resolvedDist, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $resolvedStage)) {
        Remove-Item -LiteralPath $resolvedStage -Recurse -Force
    }
}
