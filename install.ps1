param(
    [ValidateSet('codex', 'claude-code', 'agent-plugins', 'deepseek-harness')][string]$Agent = 'codex',
    [ValidateSet('install', 'rollback', 'uninstall')][string]$Action = 'install',
    [string]$Version = '1.2.0',
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

function Get-PythonRange([string]$File) {
    if (!(Test-Path -LiteralPath $File -PathType Leaf)) {
        throw "[install.files] 找不到 Python 版本声明 $File。请核对安装文件是否完整。"
    }
    $declaration = Get-Content -Raw -Encoding UTF8 -LiteralPath $File
    if ($declaration -notmatch '(?m)^requires-python[ \t]*=[ \t]*">=3\.(\d+),<3\.(\d+)"[ \t]*\r?$' -or
        [int]$Matches[1] -ge [int]$Matches[2]) {
        throw "[install.files] 无法识别 $File 中的 Python 版本范围。"
    }
    @{ Min = [int]$Matches[1]; Max = [int]$Matches[2] }
}

function Find-SupportedPython([string]$Executable, [hashtable]$Range, [string[]]$Selector = @()) {
    if (!$Executable -or !(Test-Path -LiteralPath $Executable -PathType Leaf)) { return }
    # An unavailable launcher version can write to stderr and return nonzero.
    $ErrorActionPreference = 'Continue'
    $PSNativeCommandUseErrorActionPreference = $false
    # Windows PowerShell strips embedded double quotes from native command arguments.
    $probe = 'import json,platform,sys; ok = sys.platform == ''win32'' and platform.machine().lower() in (''amd64'', ''x86_64'') and sys.maxsize >= 2**32 and sys.implementation.name == ''cpython'' and (3, int(sys.argv[1])) <= sys.version_info[:2] < (3, int(sys.argv[2])); print(json.dumps(sys.executable)) if ok else sys.exit(1)'
    $answer = @(& $Executable @Selector -I -X utf8 -B -c $probe $Range.Min $Range.Max 2>$null)
    if ($LASTEXITCODE -eq 0 -and $answer.Count -eq 1) {
        try {
            $resolved = ConvertFrom-Json -InputObject $answer[0] -ErrorAction Stop
        } catch {
            return
        }
        if ($resolved -is [string] -and $resolved -match '^(?:[a-z]:[\\/]|[\\/]{2})' -and
            (Test-Path -LiteralPath $resolved -PathType Leaf)) { return $resolved }
    }
}

function Find-InstallerPython([hashtable]$Range, [string]$Explicit, [string[]]$Retained = @()) {
    if ($Explicit) {
        $requested = Get-Command -Name $Explicit -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($requested.Source -notmatch '[\\/]Microsoft[\\/]WindowsApps[\\/]') {
            Find-SupportedPython $requested.Source $Range
        }
        return
    }
    foreach ($candidate in $Retained) {
        $resolved = Find-SupportedPython $candidate $Range
        if ($resolved) { return $resolved }
    }
    foreach ($candidate in @(Get-Command python.exe -All -CommandType Application -ErrorAction SilentlyContinue)) {
        if ($candidate.Source -match '[\\/]Microsoft[\\/]WindowsApps[\\/]') { continue }
        $resolved = Find-SupportedPython $candidate.Source $Range
        if ($resolved) { return $resolved }
    }
    $launchers = @(Get-Command py.exe -All -CommandType Application -ErrorAction SilentlyContinue)
    if (!$launchers.Count) { return }
    $launcherEnv = @{
        PYLAUNCHER_ALLOW_INSTALL = $null
        PYLAUNCHER_ALWAYS_INSTALL = $null
        PYTHON_MANAGER_AUTOMATIC_INSTALL = 'false'
    }
    $savedEnv = @{}
    try {
        foreach ($name in $launcherEnv.Keys) {
            $savedEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
            [Environment]::SetEnvironmentVariable($name, $launcherEnv[$name], 'Process')
        }
        foreach ($launcher in $launchers) {
            for ($minor = $Range.Max - 1; $minor -ge $Range.Min; $minor--) {
                $resolved = Find-SupportedPython $launcher.Source $Range @("-3.$minor")
                if ($resolved) { return $resolved }
            }
        }
    } finally {
        foreach ($name in $savedEnv.Keys) {
            [Environment]::SetEnvironmentVariable($name, $savedEnv[$name], 'Process')
        }
    }
}

function Get-RetainedHome($Record, [string]$InstallRoot) {
    $directory = [IO.Path]::GetFullPath($Record.home)
    $prefix = $InstallRoot.TrimEnd('\') + '\'
    if (!$directory.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw '[install.state] 安装记录中的路径超出选定的安装根目录。'
    }
    $directory
}

# Recovery uses the retained installation at the selected root.
if ($Action -ne 'install') {
    if ($Agent -in @('agent-plugins', 'deepseek-harness')) {
        throw '[install.arguments] 请在对应客户端中管理插件登记、回退或卸载。已准备的文件保存在本地。'
    }
    $recordName = $Agent + '.json'
    $recordPath = Join-Path $Root $recordName
    try {
        $installRoot = (Get-Item -LiteralPath $recordPath).DirectoryName
        $state = Get-Content -Raw -Encoding UTF8 -LiteralPath $recordPath | ConvertFrom-Json
    } catch {
        throw "[install.state] 无法读取安装记录 $recordPath。请核对原安装使用的 -Root。`n详细原因 $($_.Exception.Message)"
    }
    if ($state.schema -ne 1) { throw '[install.state] 无法识别安装记录的版本。' }
    if ($Agent -eq 'codex' -and $state.pending_rollback_retirement -and
        ($Action -ne 'rollback' -or $state.current.version -ne $Version)) {
        throw '[install.state] 请先用当前版本完成尚未结束的 Codex 回退。'
    }
    $target = $null
    if ($Action -eq 'rollback') {
        if ($Agent -eq 'codex' -and $state.current.version -eq $Version) {
            $target = $state.current
        } else {
            $target = $state.history | Where-Object { $_.version -eq $Version } | Select-Object -Last 1
        }
        if (!$target) { throw "[install.state] 找不到保留的版本 $Version。请核对 -Root 和 -Version。" }
    }
    $owned = $state.current
    if (!$owned -and $target) { $owned = $target }
    if (!$owned -and $state.history.Count) { $owned = $state.history[-1] }
    if (!$owned) { throw '[install.state] 当前目录没有此安装器登记的安装记录。' }
    $ownedHome = Get-RetainedHome $owned $installRoot
    $bundle = Join-Path $ownedHome 'miliastra-wonderland'
    $runner = Join-Path $bundle 'scripts/install_plugin.py'
    if (!(Test-Path -LiteralPath $runner -PathType Leaf)) {
        throw '[install.files] 已保留的安装缺少 scripts/install_plugin.py。请核对安装根目录。'
    }
    $retained = @(Join-Path $ownedHome 'runtime/Scripts/python.exe')
    if ($target -and $target -ne $owned) {
        $targetHome = Get-RetainedHome $target $installRoot
        $retained += Join-Path $targetHome 'runtime/Scripts/python.exe'
    }
    $range = Get-PythonRange (Join-Path $bundle 'pyproject.toml')
    $bootstrapPython = Find-InstallerPython $range $Python $retained
    if (!$bootstrapPython) {
        $retry = ".\install.ps1 -Agent $Agent -Action $Action -Root '" + $installRoot.Replace("'", "''") + "'"
        if ($Action -eq 'rollback') { $retry += " -Version '$Version'" }
        $retry += " -Python 'C:\路径\python.exe'"
        throw "[runtime.python] 找不到可启动恢复程序的兼容 Python。请指定可用的 Windows x64 版 CPython 3.$($range.Min)–3.$($range.Max - 1)。`n下一步 $retry"
    }
    Invoke-MiliastraInstaller $bootstrapPython @('-X', 'utf8', '-B', $runner, $Action, '--agent', $Agent, '--root', $installRoot, '--version', $Version)
    return
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
        $archivePrefix = if ($zip.GetEntry('plugin.json')) { '' } else { 'miliastra-wonderland/' }
        $bootstrap = 'scripts/install_plugin.py'
        $entries = @($bootstrap, 'pyproject.toml', 'scripts/runtime_policy.py')
        New-Item -ItemType Directory -Path (Join-Path $taskTemp 'scripts') | Out-Null
        foreach ($file in $entries) {
            $entry = @($zip.Entries | Where-Object { $_.FullName -ceq ($archivePrefix + $file) })
            if ($entry.Count -ne 1) { throw "[install.files] ZIP 中的安装文件 $file 缺失或重复。请重新打包。" }
            [IO.Compression.ZipFileExtensions]::ExtractToFile($entry[0], (Join-Path $taskTemp $file))
        }
        $runner = Join-Path $taskTemp $bootstrap
    } finally { $zip.Dispose() }
    $range = Get-PythonRange (Join-Path $taskTemp 'pyproject.toml')
    $bootstrapPython = Find-InstallerPython $range $Python
    if (!$bootstrapPython) {
        throw "[runtime.python] 请安装 Windows x64 版 CPython 3.$($range.Min)–3.$($range.Max - 1)，并通过 -Python 指定其可执行文件。"
    }
    $arguments = @('-X', 'utf8', '-B', $runner, $Action, '--agent', $Agent, '--root', $Root, '--version', $Version,
                   '--archive', $Archive, '--sha256', $Sha256, '--project', $Project, '--outputs', $Outputs)
    if ($Resume) { $arguments += '--resume' }
    Invoke-MiliastraInstaller $bootstrapPython $arguments
} finally {
    $resolvedTemp = [IO.Path]::GetFullPath($taskTemp)
    $allowedTemp = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (!$resolvedTemp.StartsWith($allowedTemp, [StringComparison]::OrdinalIgnoreCase)) { throw '[install.files] 临时路径超出系统临时目录。' }
    Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
}
