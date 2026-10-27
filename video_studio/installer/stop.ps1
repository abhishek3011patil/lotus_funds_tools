[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$rootPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtimePath = Join-Path $rootPath '.runtime'
$serverPath = Join-Path $runtimePath 'server.json'
$expectedPython = Join-Path $runtimePath 'python\python.exe'
$expectedScript = '"' + (Join-Path $rootPath 'launch.py') + '"'

try {
    if (-not (Test-Path -LiteralPath $serverPath)) {
        Write-Host 'No installed Video Studio process is recorded. It may already be closed.'
        exit 0
    }
    $server = Get-Content -LiteralPath $serverPath -Raw | ConvertFrom-Json
    $process = Get-Process -Id ([int]$server.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) {
        Remove-Item -LiteralPath $serverPath -Force
        Write-Host 'Video Studio is already stopped.'
        exit 0
    }
    $details = Get-CimInstance Win32_Process -Filter ("ProcessId=" + [int]$server.pid)
    $matches = $process.StartTime.ToUniversalTime().Ticks -eq [long]$server.started -and
        $details.ExecutablePath -eq $expectedPython -and
        $details.CommandLine.Contains($expectedScript)
    if (-not $matches) {
        throw 'The recorded process no longer matches this app. No process was stopped.'
    }
    Stop-Process -Id $process.Id -ErrorAction Stop
    Remove-Item -LiteralPath $serverPath -Force
    Write-Host 'Video Studio stopped. Open Launch.cmd to start it again.'
} catch {
    Write-Host "Could not stop Video Studio: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
exit 0
