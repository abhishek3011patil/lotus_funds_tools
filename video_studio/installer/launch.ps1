[CmdletBinding()]
param([switch]$SkipInstall, [switch]$NoDialog)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'common.ps1')
$rootPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtimePath = Join-Path $rootPath '.runtime'
$pythonExe = Join-Path $runtimePath 'python\python.exe'
$readyPath = Join-Path $runtimePath 'ready.json'
$logPath = Join-Path $rootPath 'logs'

try {
    $ready = $false
    if (Test-Path -LiteralPath $pythonExe) {
        $currentHash = Get-StudioFileHash -Path (Join-Path $rootPath 'requirements.txt')
        foreach ($markerPath in @($readyPath, (Join-Path $runtimePath 'core-ready.json'))) {
            if (-not (Test-Path -LiteralPath $markerPath)) { continue }
            try {
                $installation = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
                $ready = $installation.requirements -eq $currentHash
                if ($ready) { break }
            } catch { $ready = $false }
        }
    }
    if (-not $ready) {
        if ($SkipInstall) { throw 'The private runtime is incomplete. Run Install.cmd again.' }
        Write-Host 'Preparing the local runtime. First setup needs internet and may take a few minutes.'
        Write-Host 'Setup details are recorded in logs\install.log.'
        $powershellExe = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
        $installArguments = '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot 'install.ps1') + '" -NoLaunch'
        $setup = Start-Process -FilePath $powershellExe -ArgumentList $installArguments -WindowStyle Hidden -PassThru -Wait
        if ($setup.ExitCode -ne 0) { throw 'Setup did not finish. See logs\install.log and run Install.cmd again.' }
    }
    New-Item -ItemType Directory -Force -Path $logPath | Out-Null
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $runtimePath 'browsers'
    $env:PYTHONNOUSERSITE = '1'
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
    $errorLog = Join-Path $logPath "launch-$stamp-error.log"
    $process = Start-Process -FilePath $pythonExe -ArgumentList ('"' + (Join-Path $rootPath 'launch.py') + '"') -WorkingDirectory $rootPath -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $logPath "launch-$stamp.log") -RedirectStandardError $errorLog
    Start-Sleep -Seconds 2
    if ($process.HasExited -and $process.ExitCode -ne 0) {
        throw "The application stopped during startup. Details: $errorLog"
    }
    if (-not $process.HasExited) {
        @{ pid = $process.Id; started = $process.StartTime.ToUniversalTime().Ticks } |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'server.json') -Encoding UTF8
    }
} catch {
    $message = $_.Exception.Message
    Write-Error -Message $message -ErrorAction Continue
    if (-not $NoDialog) {
        try {
            Add-Type -AssemblyName System.Windows.Forms
            [System.Windows.Forms.MessageBox]::Show($message, 'Tarkash Video Studio', 'OK', 'Error') | Out-Null
        } catch { }
    }
    exit 1
}
exit 0
