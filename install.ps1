param(
    [ValidateSet('codex', 'claude-code', 'agent-plugins', 'deepseek-harness')][string]$Agent = 'codex',
    [ValidateSet('install', 'rollback', 'uninstall')][string]$Action = 'install',
    [string]$Version = '1.1.0',
    [switch]$Resume,
    [string]$Project, [string]$Outputs, [string]$Python,
    [string]$Root, [string]$Archive, [string]$Sha256
)
$ErrorActionPreference = 'Stop'
if ($Resume -and $Action -ne 'install') { throw '[install.arguments] -Resume 仅用于继续安装。' }
if ($env:OS -ne 'Windows_NT') { throw '[runtime.platform] 完整安装包需要 Windows x64。' }
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw '[install.arguments] -Version 需使用 x.y.z 格式。' }
if (!$Root) { $Root = Join-Path $env:LOCALAPPDATA 'Miliastra Wonderland' }

function Invoke-MiliastraInstaller([string]$Executable, [string[]]$Arguments) {
    $consoleEncoding = [Console]::OutputEncoding
    try {
        [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) { throw "[install.operation] 安装器执行失败，退出码 $LASTEXITCODE。请查看上方错误。" }
    } finally {
        [Console]::OutputEncoding = $consoleEncoding
    }
}
# Recovery uses the retained installation at the selected root.
if ($Action -ne 'install') {
    if ($Agent -in @('agent-plugins', 'deepseek-harness')) {
        throw '[install.arguments] 请在对应客户端中管理插件登记、回退或卸载。已准备的文件保存在本地。'
    }
    $recordName = $Agent + '.json'
    $recordPath = Join-Path $Root $recordName
    try {
        $state = Get-Content -Raw -Encoding UTF8 -LiteralPath $recordPath | ConvertFrom-Json
    } catch {
        throw "[install.state] 无法读取安装记录 $recordPath。请核对原安装使用的 -Root。`n详细原因 $($_.Exception.Message)"
    }
    if ($state.schema -ne 1) { throw '[install.state] 无法识别安装记录的版本。' }
    $owned = $state.current
    if (!$owned -and $state.history.Count) { $owned = $state.history[-1] }
    if (!$owned) { throw '[install.state] 当前目录没有此安装器登记的安装记录。' }
    $ownedHome = [IO.Path]::GetFullPath($owned.home)
    $ownedRoot = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    if (!$ownedHome.StartsWith($ownedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw '[install.state] 安装记录中的路径超出选定的安装根目录。' }
    $runner = Join-Path $ownedHome 'miliastra-wonderland/scripts/install_plugin.py'
    if (!(Test-Path -LiteralPath $runner -PathType Leaf)) {
        throw '[install.files] 已保留的安装缺少 scripts/install_plugin.py。请核对安装根目录。'
    }
    $boundPython = Join-Path $ownedHome 'runtime/Scripts/python.exe'
    Invoke-MiliastraInstaller $boundPython @('-X', 'utf8', '-B', $runner, $Action, '--agent', $Agent, '--root', $Root, '--version', $Version)
    return
}

function Find-SupportedPython([string]$Executable, [string[]]$Selector = @()) {
    if (!$Executable -or $Executable -match '[\\/]Microsoft[\\/]WindowsApps[\\/]') { return }
    # An unavailable launcher version can write to stderr and return nonzero.
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    # Windows PowerShell strips embedded double quotes from native command arguments.
    $probe = 'import json,sys; sys.exit(1) if not ((3, int(sys.argv[1])) <= sys.version_info[:2] < (3, int(sys.argv[2]))) or sys.implementation.name != ''cpython'' or sys.maxsize < 2**32 else print(json.dumps(sys.executable))'
    $answer = @(& $Executable @Selector -I -B -c $probe $minMinor $maxMinor 2>$null)
    if ($LASTEXITCODE -eq 0 -and $answer.Count -eq 1) {
        $resolved = ConvertFrom-Json -InputObject $answer[0] -ErrorAction SilentlyContinue
        if ($resolved -is [string] -and (Test-Path -LiteralPath $resolved -PathType Leaf)) { return $resolved }
    }
}

if (!$Archive -or $Sha256 -notmatch '^[0-9a-fA-F]{64}$') {
    throw '[install.archive] 请用 -Archive 指定本地打包的 ZIP，并用 -Sha256 提供打包输出的 SHA-256。操作见 docs/installation.md。'
}
if (!(Test-Path -LiteralPath $Archive -PathType Leaf)) { throw "[install.archive] 找不到安装包 $Archive。请核对 -Archive 路径。" }
if ((Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash -ne $Sha256) {
    throw '[install.archive] ZIP 的 SHA-256 校验失败。请核对打包输出的摘要和 -Archive 指向的文件。'
}
if (!$Project) { $Project = Read-Host '请输入已有工程目录' }
if (!$Outputs) { $Outputs = Read-Host '请输入工程目录之外的独立输出目录' }

$taskTemp = Join-Path ([IO.Path]::GetTempPath()) ('miliastra-wonderland-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $taskTemp | Out-Null
try {
    # Extract only the verified bootstrap, leaving full archive validation to it.
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead((Resolve-Path -LiteralPath $Archive).Path)
    try {
        $archiveRoot = 'miliastra-wonderland'
        $bootstrap = 'scripts/install_plugin.py'
        $entries = @($bootstrap, 'pyproject.toml', 'scripts/runtime_policy.py')
        $contract = $zip.GetEntry("$archiveRoot/pyproject.toml")
        if (!$contract) { throw "[install.files] ZIP 缺少 $archiveRoot/pyproject.toml。请核对 ZIP 是否为完整安装包。" }
        $reader = New-Object IO.StreamReader($contract.Open())
        try { $declaration = $reader.ReadToEnd() } finally { $reader.Dispose() }
        if ($declaration -notmatch '(?m)^requires-python\s*=\s*">=3\.(\d+),<3\.(\d+)"\s*$') {
            throw '[install.files] ZIP 中的 pyproject.toml 包含无法识别的 Python 版本范围。'
        }
        $minMinor = [int]$Matches[1]
        $maxMinor = [int]$Matches[2]
        New-Item -ItemType Directory -Path (Join-Path $taskTemp 'scripts') | Out-Null
        foreach ($file in $entries) {
            $entry = @($zip.Entries | Where-Object { $_.FullName -ceq "$archiveRoot/$file" })
            if ($entry.Count -ne 1) { throw "[install.files] ZIP 中的安装文件 $file 缺失或重复。请重新打包。" }
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
    if (!$Python) { throw "[runtime.python] 请安装 Windows x64 版 CPython 3.$minMinor–3.$($maxMinor - 1)，并通过 -Python 指定其可执行文件。" }
    $arguments = @('-X', 'utf8', '-B', $runner, $Action, '--agent', $Agent, '--root', $Root, '--version', $Version)
    if ($Action -eq 'install') { $arguments += @('--archive', $Archive, '--sha256', $Sha256, '--project', $Project, '--outputs', $Outputs) }
    if ($Resume) { $arguments += '--resume' }
    Invoke-MiliastraInstaller $Python $arguments
} finally {
    $resolvedTemp = [IO.Path]::GetFullPath($taskTemp)
    $allowedTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (!$resolvedTemp.StartsWith($allowedTemp, [StringComparison]::OrdinalIgnoreCase)) { throw '[install.files] 临时路径超出系统临时目录。' }
    Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
}
