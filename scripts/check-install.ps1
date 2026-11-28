$consoleEncoding = [Console]::OutputEncoding
try {
    [Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
    $launcher = Join-Path $PSScriptRoot 'mcp_launcher.cjs'
    if (!(Test-Path -LiteralPath $launcher -PathType Leaf)) {
        Write-Host '[install.files] 插件缺少 MCP 启动脚本。'
        Write-Host "缺少文件 $launcher"
        Write-Host '下一步 通过原安装入口重新安装插件，或完整解压原 ZIP 后再运行自检。'
        exit 2
    }

    # Enumerate applications directly so a missing Node does not trigger module autoload.
    $node = $ExecutionContext.InvokeCommand.GetCommands(
        'node', [System.Management.Automation.CommandTypes]::Application, $false
    ) | Select-Object -First 1
    if (!$node) {
        Write-Host '[runtime.node] 当前 PowerShell 的 PATH 找不到 Node.js。'
        Write-Host '下一步 安装 Windows x64 版 Node.js 22 或更高版本（DeepSeek Harness 需要 24.9+）。重新打开终端，确认 node --version 能运行，然后重试。'
        exit 2
    }

    & $node.Source $launcher --check
    exit $LASTEXITCODE
} finally {
    [Console]::OutputEncoding = $consoleEncoding
}
