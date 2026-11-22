param(
    [ValidateSet('codex', 'claude-code', 'agent-plugins', 'deepseek-harness')][string]$Agent = 'codex',
    [ValidateSet('install', 'rollback', 'uninstall')][string]$Action = 'install',
    [string]$Version = '4.1.1',
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
    if ($Agent -in @('agent-plugins', 'deepseek-harness')) {
        throw 'Manage registration and rollback in the host. The prepared files are retained.'
    }
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
function Find-SupportedPython([string]$Executable, [string[]]$Selector = @()) {
    if (!$Executable -or $Executable -match '[\\/]Microsoft[\\/]WindowsApps[\\/]') { return }
    # An unavailable launcher version can write to stderr and return nonzero.
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    $probe = 'import json,sys; sys.exit(1) if sys.version_info[:2] not in ((3, 11), (3, 12)) else print(json.dumps(sys.executable))'
    $answer = @(& $Executable @Selector -I -B -c $probe 2>$null)
    if ($LASTEXITCODE -eq 0 -and $answer.Count -eq 1) {
        $resolved = ConvertFrom-Json -InputObject $answer[0] -ErrorAction SilentlyContinue
        if ($resolved -is [string] -and (Test-Path -LiteralPath $resolved -PathType Leaf)) { return $resolved }
    }
}

if ($Python) {
    $requested = Get-Command -Name $Python -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
    $Python = Find-SupportedPython $requested.Source
} else {
    foreach ($candidate in @(Get-Command python.exe -All -CommandType Application -ErrorAction SilentlyContinue)) {
        $Python = Find-SupportedPython $candidate.Source
        if ($Python) { break }
    }
    if (!$Python) {
        foreach ($launcher in @(Get-Command py.exe -All -CommandType Application -ErrorAction SilentlyContinue)) {
            foreach ($selector in @('-3.12', '-3.11')) {
                $Python = Find-SupportedPython $launcher.Source @($selector)
                if ($Python) { break }
            }
            if ($Python) { break }
        }
    }
}
if (!$Python) { throw 'A usable Python 3.11-3.12 is required. Install it or pass its executable with -Python.' }
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
        $uri = 'https://api.github.com/repos/savormundane/Genshin-UGC-plugin/releases/tags/v' + $Version
        $release = Invoke-RestMethod $uri -UseBasicParsing -TimeoutSec 30 -Headers @{ Accept = 'application/vnd.github+json' }
        $asset = @($release.assets | Where-Object { $_.name -ceq $filename })
        if ($release.tag_name -cne ('v' + $Version) -or $release.draft -ne $false -or
            $asset.Count -ne 1 -or $asset[0].state -ne 'uploaded' -or
            $asset[0].digest -notmatch '^sha256:([0-9a-fA-F]{64})$') {
            throw 'The release must publish one Windows ZIP with a GitHub SHA-256 digest.'
        }
        $Sha256 = $asset[0].digest.Substring(7)
        $Archive = Join-Path $taskTemp $filename
        Invoke-WebRequest ($base + '/' + $filename) -UseBasicParsing -OutFile $Archive
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
