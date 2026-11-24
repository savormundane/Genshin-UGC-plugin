param(
    [ValidateSet('codex', 'claude-code', 'agent-plugins', 'deepseek-harness')][string]$Agent = 'codex',
    [ValidateSet('install', 'rollback', 'uninstall')][string]$Action = 'install',
    [string]$Version = '1.1.0',
    [switch]$Resume,
    [string]$Project, [string]$Outputs, [string]$Python,
    [string]$Root, [string]$Archive, [string]$Sha256
)
$ErrorActionPreference = 'Stop'
if ($Resume -and $Action -ne 'install') { throw '-Resume is only valid for install.' }
if ($env:OS -ne 'Windows_NT') { throw 'The complete bundle currently supports Windows x64 only.' }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must be x.y.z.' }
$explicitRoot = [bool]$Root
if (!$Root) { $Root = Join-Path $env:LOCALAPPDATA 'Miliastra Wonderland' }
$legacyRoot = Join-Path $env:LOCALAPPDATA 'Genshin-UGC-Public'
# Recovery must also work offline, without downloading an old release bootstrap.
if ($Action -ne 'install') {
    if ($Agent -in @('agent-plugins', 'deepseek-harness')) {
        throw 'Manage registration and rollback in the host. The prepared files are retained.'
    }
    $recordName = $Agent + '.json'
    if (!$explicitRoot -and !(Test-Path -LiteralPath (Join-Path $Root $recordName)) -and
        (Test-Path -LiteralPath (Join-Path $legacyRoot $recordName))) { $Root = $legacyRoot }
    $state = Get-Content -Raw -Encoding UTF8 -LiteralPath (Join-Path $Root $recordName) | ConvertFrom-Json
    if ($state.schema -ne 1) { throw 'Unknown installation state version.' }
    $owned = $state.current
    if (!$owned -and $state.history.Count) { $owned = $state.history[-1] }
    if (!$owned) { throw 'No retained installation owned by this installer.' }
    $ownedHome = [IO.Path]::GetFullPath($owned.home)
    $ownedRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    if (!$ownedHome.StartsWith($ownedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw 'Installation is outside the selected root.' }
    $runner = Join-Path $ownedHome 'miliastra-wonderland/scripts/install_plugin.py'
    if (!(Test-Path -LiteralPath $runner -PathType Leaf)) {
        $runner = Join-Path $ownedHome 'Genshin-UGC/scripts/install_public.py'
    }
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
    $probe = 'import json,sys; sys.exit(1) if not ((3, int(sys.argv[1])) <= sys.version_info[:2] < (3, int(sys.argv[2]))) or sys.implementation.name != "cpython" or sys.maxsize < 2**32 else print(json.dumps(sys.executable))'
    $answer = @(& $Executable @Selector -I -B -c $probe $minMinor $maxMinor 2>$null)
    if ($LASTEXITCODE -eq 0 -and $answer.Count -eq 1) {
        $resolved = ConvertFrom-Json -InputObject $answer[0] -ErrorAction SilentlyContinue
        if ($resolved -is [string] -and (Test-Path -LiteralPath $resolved -PathType Leaf)) { return $resolved }
    }
}

if (!$Archive -or $Sha256 -notmatch '^[0-9a-fA-F]{64}$') {
    throw 'Provide the locally built ZIP with -Archive and its SHA-256 with -Sha256. See docs/installation.md.'
}
if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash -ne $Sha256) { throw 'Archive SHA-256 mismatch.' }
if (!$Project) { $Project = Read-Host 'Existing project directory' }
if (!$Outputs) { $Outputs = Read-Host 'Separate output directory (outside the project)' }

$taskTemp = Join-Path ([IO.Path]::GetTempPath()) ('miliastra-wonderland-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTemp | Out-Null
try {
    # Extract only the verified bootstrap, leaving full archive validation to it.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $Archive).Path)
    try {
        $minMinor = 11
        $maxMinor = 13
        $archiveRoot = 'miliastra-wonderland'
        $bootstrap = 'scripts/install_plugin.py'
        if (!$zip.GetEntry("$archiveRoot/$bootstrap") -and $zip.GetEntry('Genshin-UGC/scripts/install_public.py')) {
            $archiveRoot = 'Genshin-UGC'
            $bootstrap = 'scripts/install_public.py'
            if (!$explicitRoot) { $Root = $legacyRoot }
        }
        $entries = @($bootstrap)
        $contract = $zip.GetEntry("$archiveRoot/pyproject.toml")
        if ($contract) {
            $reader = New-Object IO.StreamReader($contract.Open())
            try { $declaration = $reader.ReadToEnd() } finally { $reader.Dispose() }
            if ($declaration -notmatch '(?m)^requires-python\s*=\s*">=3\.(\d+),<3\.(\d+)"\s*$') {
                throw 'Invalid Python range in verified archive.'
            }
            $minMinor = [int]$Matches[1]
            $maxMinor = [int]$Matches[2]
            $entries += @('pyproject.toml', 'scripts/runtime_policy.py')
        }
        New-Item -ItemType Directory -Path (Join-Path $taskTemp 'scripts') | Out-Null
        foreach ($file in $entries) {
            $entry = @($zip.Entries | Where-Object { $_.FullName -ceq "$archiveRoot/$file" })
            if ($entry.Count -ne 1) { throw "Installer entry missing or duplicated: $file" }
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry[0], (Join-Path $taskTemp $file))
        }
        $runner = Join-Path $taskTemp $bootstrap
    } finally { $zip.Dispose() }
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
                foreach ($selector in ((($maxMinor - 1)..$minMinor) | ForEach-Object { "-3.$_" })) {
                    $Python = Find-SupportedPython $launcher.Source @($selector)
                    if ($Python) { break }
                }
                if ($Python) { break }
            }
        }
    }
    if (!$Python) { throw "CPython 3.$minMinor–3.$($maxMinor - 1) required. Pass its executable with -Python." }
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
