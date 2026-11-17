param(
    [ValidateSet('codex', 'claude-code')][string]$Agent = 'codex',
    [ValidateSet('install', 'rollback', 'uninstall')][string]$Action = 'install',
    [string]$Version = '3.7.0',
    [switch]$Resume,
    [string]$Project, [string]$Outputs, [string]$Python,
    [string]$Root, [string]$Archive, [string]$Sha256
)
$ErrorActionPreference = 'Stop'
if ($Resume -and $Action -ne 'install') { throw '-Resume is only valid for install.' }
if ($env:OS -ne 'Windows_NT') { throw 'The complete bundle currently supports Windows x64 only.' }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must be x.y.z.' }
if (!$Root) { $Root = Join-Path $env:LOCALAPPDATA 'Genshin-UGC-Public' }
# Recovery must also work offline, without downloading an old release bootstrap.
if ($Action -ne 'install') {
    $state = Get-Content -Raw -LiteralPath (Join-Path $Root ($Agent + '.json')) | ConvertFrom-Json
    if ($state.schema -ne 1) { throw 'Unknown installation state version.' }
    $owned = $state.current
    if (!$owned -and $state.history.Count) { $owned = $state.history[-1] }
    if (!$owned) { throw 'No retained installation owned by this installer.' }
    $ownedHome = [IO.Path]::GetFullPath($owned.home)
    $ownedRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    if (!$ownedHome.StartsWith($ownedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Installation is outside the selected root.' }
    $runner = Join-Path $ownedHome 'Genshin-UGC/scripts/install_public.py'
    $boundPython = Join-Path $ownedHome 'runtime/Scripts/python.exe'
    & $boundPython -X utf8 -B $runner $Action --agent $Agent --root $Root --version $Version
    if ($LASTEXITCODE -ne 0) { throw ('Installation operation failed: ' + $LASTEXITCODE) }
    return
}
if (!$Python) {
    $Python = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
    if (!$Python -and (Get-Command py.exe -ErrorAction SilentlyContinue)) {
        $Python = & py.exe -3.12 -c 'import sys; print(sys.executable)'
        if ($LASTEXITCODE -ne 0) { $Python = $null }
    }
}
if (!$Python) { throw 'Install Python 3.11-3.12 or pass -Python with its executable path. No global software was installed.' }
if ($Action -eq 'install') {
    if (!$Project) { $Project = Read-Host 'Existing project directory' }
    if (!$Outputs) { $Outputs = Read-Host 'Separate output directory (outside the project)' }
}
# A downloaded release ZIP is checked before any packaged Python is executed.
$taskTemp = Join-Path ([IO.Path]::GetTempPath()) ('genshin-ugc-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTemp | Out-Null
try {
    if (!$Archive) {
        $base = 'https://github.com/savormundane/Genshin-UGC-plugin/releases/download/v' + $Version
        $filename = 'Genshin-UGC-' + $Version + '-windows-x64.zip'
        $Archive = Join-Path $taskTemp $filename
        Invoke-WebRequest ($base + '/' + $filename) -OutFile $Archive
        $checksums = (Invoke-WebRequest ($base + '/SHA256SUMS.txt')).Content
        $line = @($checksums -split "`n" | Where-Object { $_.Trim() -match ('^[0-9a-fA-F]{64}\s+' + [regex]::Escape($filename) + '$') })
        if ($line.Count -ne 1) { throw 'Missing or ambiguous release checksum.' }
        $Sha256 = ($line[0] -split '\s+')[0]
    }
    if ($Sha256 -notmatch '^[0-9a-fA-F]{64}$') { throw 'A local ZIP requires -Sha256.' }
    if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash -ne $Sha256) { throw 'Archive SHA-256 mismatch.' }
    # Extract only the verified bootstrap, leaving full archive validation to it.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $Archive).Path)
    try {
        $entry = @($zip.Entries | Where-Object { $_.FullName -eq 'Genshin-UGC/scripts/install_public.py' })
        if ($entry.Count -ne 1) { throw 'Installer entry missing or duplicated.' }
        $runner = Join-Path $taskTemp 'install_public.py'
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry[0], $runner)
    } finally { $zip.Dispose() }
    $arguments = @('-X', 'utf8', '-B', $runner, $Action, '--agent', $Agent, '--root', $Root, '--version', $Version)
    if ($Action -eq 'install') { $arguments += @('--archive', $Archive, '--sha256', $Sha256, '--project', $Project, '--outputs', $Outputs) }
    if ($Resume) { $arguments += '--resume' }
    & $Python @arguments
    if ($LASTEXITCODE -ne 0) { throw ('Installation operation failed: ' + $LASTEXITCODE) }
} finally {
    $resolvedTemp = [IO.Path]::GetFullPath($taskTemp)
    $allowedTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (!$resolvedTemp.StartsWith($allowedTemp, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unexpected temporary path.' }
    Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
}
