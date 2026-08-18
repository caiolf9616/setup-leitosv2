param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile
)

$ErrorActionPreference = "Stop"
$resolvedRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$resolvedBackup = [System.IO.Path]::GetFullPath($BackupFile)

if (-not $resolvedBackup.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "O arquivo de backup precisa ficar dentro do projeto."
}
if (-not (Test-Path -LiteralPath $resolvedBackup -PathType Leaf)) {
    throw "Backup não encontrado: $resolvedBackup"
}

Get-Content -Raw -Encoding UTF8 -LiteralPath $resolvedBackup |
    docker compose exec -T db psql `
        --username="${env:POSTGRES_USER}" `
        --dbname="${env:POSTGRES_DB}" `
        --set ON_ERROR_STOP=on

Write-Output "Restauração concluída a partir de $resolvedBackup"
