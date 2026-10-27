param([switch]$ListVoices, [string]$RequestPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($ListVoices) {
        $voices = @($speaker.GetInstalledVoices() | Where-Object Enabled | ForEach-Object { @{id=$_.VoiceInfo.Name; name=($_.VoiceInfo.Name + ' (' + $_.VoiceInfo.Culture.Name + ')')} })
        ConvertTo-Json -InputObject $voices -Compress
    } else {
        $request = Get-Content -LiteralPath $RequestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($request.voice) { $speaker.SelectVoice($request.voice) }
        $speaker.Rate = [int]$request.rate
        $speaker.SetOutputToWaveFile($request.output)
        $speaker.Speak([string]$request.text)
        $speaker.SetOutputToNull()
    }
} finally { $speaker.Dispose() }
