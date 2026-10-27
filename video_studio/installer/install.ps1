[CmdletBinding()]
param(
    [switch]$NoLaunch,
    [switch]$NoShortcut
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
. (Join-Path $PSScriptRoot 'common.ps1')
$rootPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtimePath = Join-Path $rootPath '.runtime'
$pythonPath = Join-Path $runtimePath 'python'
$pythonExe = Join-Path $pythonPath 'python.exe'
$readyPath = Join-Path $runtimePath 'ready.json'
$logPath = Join-Path $rootPath 'logs'
$requirementsPath = Join-Path $rootPath 'requirements.txt'
$pythonVersion = '3.13.17'
$pythonUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-amd64.zip"
$pythonSha256 = '9e35319bffedab8b36ad44d8f377cb4f1733bcec257a0b6d04d94f01486ddb38'
$transcriptStarted = $false
$lockStream = $null

function Invoke-Download {
    param([string]$Uri, [string]$Destination)
    for ($attempt = 1; $attempt -le 3; $attempt++) {
        try {
            Invoke-WebRequest -Uri $Uri -OutFile $Destination -UseBasicParsing -TimeoutSec 180
            return
        } catch {
            if ($attempt -eq 3) { throw }
            Write-Host "Download interrupted. Retrying ($attempt of 3)..."
            Start-Sleep -Seconds (2 * $attempt)
        }
    }
}

function Invoke-Python {
    param([string[]]$Arguments)
    & $pythonExe @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "A setup step failed (exit code $LASTEXITCODE). See logs\install.log for details."
    }
}

try {
    if (-not [Environment]::Is64BitOperatingSystem) {
        throw 'This installer requires 64-bit Windows 10 or 11.'
    }
    if ($env:PROCESSOR_ARCHITECTURE -eq 'ARM64' -or $env:PROCESSOR_ARCHITEW6432 -eq 'ARM64') {
        throw 'This package is for Intel/AMD 64-bit Windows. ARM Windows is not currently supported.'
    }
    foreach ($requiredFile in @('app.py', 'launch.py', 'requirements.txt', 'scripts\setup_voices.py')) {
        if (-not (Test-Path -LiteralPath (Join-Path $rootPath $requiredFile) -PathType Leaf)) {
            throw "The application folder is incomplete: $requiredFile is missing. Extract the entire ZIP before running setup."
        }
    }
    New-Item -ItemType Directory -Force -Path $runtimePath, $logPath | Out-Null
    try {
        $lockStream = [IO.File]::Open((Join-Path $runtimePath 'install.lock'), 'OpenOrCreate', 'ReadWrite', 'None')
    } catch {
        throw 'Setup is already running. Please wait for the other setup window to finish.'
    }
    Start-Transcript -LiteralPath (Join-Path $logPath 'install.log') -Append | Out-Null
    $transcriptStarted = $true
    Write-Host ''
    Write-Host 'Tarkash Video Studio - local setup' -ForegroundColor Cyan
    Write-Host "Application folder: $rootPath"
    Write-Host 'First setup needs internet and may take a few minutes.'
    Write-Host 'Python, video tools, the rendering browser and local voice models stay inside this folder.'
    Write-Host 'The high-quality local voice pack is approximately 337 MiB. Narration text is never uploaded.'
    Write-Host ''
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $runtimePath 'browsers'
    $env:PYTHONNOUSERSITE = '1'
    $env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
    $requirementsHash = Get-StudioFileHash -Path $requirementsPath
    $alreadyReady = $false
    if ((Test-Path -LiteralPath $readyPath) -and (Test-Path -LiteralPath $pythonExe)) {
        try {
            $ready = Get-Content -LiteralPath $readyPath -Raw | ConvertFrom-Json
            $alreadyReady = ($ready.python -eq $pythonVersion -and $ready.requirements -eq $requirementsHash)
        } catch { $alreadyReady = $false }
    }
    if ($alreadyReady) {
        Write-Host 'Existing installation found. Checking it...'
        try {
            Invoke-Python -Arguments @((Join-Path $PSScriptRoot 'verify_runtime.py'))
            Invoke-Python -Arguments @('-c', 'import kokoro_onnx, onnxruntime, phonemizer, espeakng_loader')
        } catch {
            Write-Host 'The existing runtime needs repair. Reinstalling its dependencies...'
            $alreadyReady = $false
        }
    }
    if (Test-Path -LiteralPath $readyPath) { Remove-Item -LiteralPath $readyPath -Force }
    if (-not $alreadyReady) {
        $downloadsPath = Join-Path $runtimePath 'downloads'
        New-Item -ItemType Directory -Force -Path $downloadsPath, $pythonPath | Out-Null
        $existingPythonVersion = ''
        if (Test-Path -LiteralPath $pythonExe) {
            try {
                $existingPythonVersion = (& $pythonExe -c 'import platform; print(platform.python_version())' | Out-String).Trim()
                if ($LASTEXITCODE -ne 0) { $existingPythonVersion = '' }
            } catch { $existingPythonVersion = '' }
        }
        if ($existingPythonVersion -ne $pythonVersion) {
            $pythonArchive = Join-Path $downloadsPath "python-$pythonVersion-embed-amd64.zip"
            $archiveValid = (Test-Path -LiteralPath $pythonArchive) -and ((Get-StudioFileHash -Path $pythonArchive) -eq $pythonSha256)
            if (-not $archiveValid) {
                Write-Host '[1/5] Downloading private Python runtime...'
                Invoke-Download -Uri $pythonUrl -Destination $pythonArchive
            }
            if ((Get-StudioFileHash -Path $pythonArchive) -ne $pythonSha256) {
                throw 'Python download checksum did not match Python.org. No downloaded program was run; rerun setup to retry.'
            }
            Expand-Archive -LiteralPath $pythonArchive -DestinationPath $pythonPath -Force
        } else {
            Write-Host "[1/5] Reusing private Python $pythonVersion."
        }
        @('python313.zip', '.', 'Lib\site-packages', '..\..', 'import site') | Set-Content -LiteralPath (Join-Path $pythonPath 'python313._pth') -Encoding ASCII
        Write-Host '[2/5] Installing local application dependencies...'
        if (-not (Test-Path -LiteralPath (Join-Path $pythonPath 'Lib\site-packages\pip\__init__.py'))) {
            $getPipPath = Join-Path $downloadsPath 'get-pip.py'
            Invoke-Download -Uri 'https://bootstrap.pypa.io/get-pip.py' -Destination $getPipPath
            Invoke-Python -Arguments @($getPipPath, '--disable-pip-version-check', '--no-warn-script-location', 'pip==26.2.2')
        }
        Invoke-Python -Arguments @('-m', 'pip', '--isolated', 'install', '--disable-pip-version-check', '--no-warn-script-location', '--only-binary=:all:', '-r', $requirementsPath)
        Invoke-Python -Arguments @('-m', 'pip', 'check')
        Write-Host '[3/5] Installing the private video rendering browser...'
        Invoke-Python -Arguments @('-m', 'playwright', 'install', 'chromium')
    }
    # Preserve access to Windows narration if the separate neural voice setup fails.
    Invoke-Python -Arguments @((Join-Path $PSScriptRoot 'verify_runtime.py'))
    @{ python = $pythonVersion; requirements = $requirementsHash; coreOnly = $true; installed = [DateTime]::UtcNow.ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runtimePath 'core-ready.json') -Encoding UTF8
    Write-Host '[4/5] Preparing the private high-quality voice pack...'
    Invoke-Python -Arguments @((Join-Path $rootPath 'scripts\setup_voices.py'))
    Write-Host '[5/5] Checking video rendering and local speech generation...'
    Invoke-Python -Arguments @((Join-Path $PSScriptRoot 'verify_runtime.py'), '--require-voices')
    @{ python = $pythonVersion; requirements = $requirementsHash; voices = 'kokoro-v1.0-full'; installed = [DateTime]::UtcNow.ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath $readyPath -Encoding UTF8
    if (-not $NoShortcut) {
        try {
            $desktopPath = [Environment]::GetFolderPath('Desktop')
            $shell = New-Object -ComObject WScript.Shell
            $shortcut = $shell.CreateShortcut((Join-Path $desktopPath 'Tarkash Video Studio.lnk'))
            $shortcut.TargetPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
            $shortcut.Arguments = '-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' + (Join-Path $PSScriptRoot 'launch.ps1') + '"'
            $shortcut.WorkingDirectory = $rootPath
            $shortcut.Description = 'Create branded market videos locally'
            $shortcut.WindowStyle = 7
            $shortcut.Save()
            Write-Host 'Desktop shortcut created.'
        } catch {
            Write-Warning "The desktop shortcut could not be created. You can still open Launch.cmd. $($_.Exception.Message)"
        }
    }
    Write-Host ''
    Write-Host 'Setup completed successfully.' -ForegroundColor Green
} catch {
    Write-Host ''
    Write-Host "Setup failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Details: $(Join-Path $logPath 'install.log')"
    Write-Host 'Check your internet connection, keep the complete application folder, and run Install.cmd again.'
    exit 1
} finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
    if ($null -ne $lockStream) { $lockStream.Dispose() }
}

if (-not $NoLaunch) {
    & (Join-Path $PSScriptRoot 'launch.ps1') -SkipInstall -NoDialog
    exit $LASTEXITCODE
}
exit 0
