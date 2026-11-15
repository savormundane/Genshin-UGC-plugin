param(
    [Parameter(Mandatory = $true)][string]$SessionDirectory,
    [Parameter(Mandatory = $true)][string[]]$CommandArgs,
    [string]$ToolPath
)
$ErrorActionPreference = 'Stop'
if (-not $ToolPath) {
    if ($env:GEIMG_EXE) { $ToolPath = $env:GEIMG_EXE }
    else { $ToolPath = Join-Path $PSScriptRoot '..\..\..\runtime\GE_IMG_Tool.exe' }
}
$ToolPath = (Resolve-Path -LiteralPath $ToolPath).Path
$sessionPath = [IO.Path]::GetFullPath($SessionDirectory)
if ($CommandArgs.Count -eq 0) { throw 'CommandArgs must contain a GEIMG command.' }
if ($CommandArgs -contains '--session' -or $CommandArgs -contains '--session-dir') {
    throw 'Use SessionDirectory to keep every command in the same isolated session.'
}
New-Item -ItemType Directory -Force -Path $sessionPath | Out-Null
$callArgs = @($CommandArgs) + @('--session-dir', $sessionPath)
if ($CommandArgs -notcontains '--json') { $callArgs += '--json' }
& $ToolPath @callArgs
exit $LASTEXITCODE
