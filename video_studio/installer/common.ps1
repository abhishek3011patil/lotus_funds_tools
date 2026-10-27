# A launcher may inherit PowerShell 7's module path when starting Windows PowerShell.
# Put the current host's built-in modules first without changing machine settings.
$studioModulePath = Join-Path $PSHOME 'Modules'
$env:PSModulePath = $studioModulePath + [IO.Path]::PathSeparator + $env:PSModulePath

function Get-StudioFileHash {
    param([Parameter(Mandatory = $true)][string]$Path)
    $stream = [IO.File]::OpenRead($Path)
    $sha = [Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '')
    } finally {
        $sha.Dispose()
        $stream.Dispose()
    }
}
