param(
    [string]$OutputDirectory = ".\deploy\backups"
)

$ErrorActionPreference = "Stop"
$resolvedRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $resolvedRoot $OutputDirectory))

if (-not $resolvedOutput.StartsWith($resolvedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "O diretório de backup precisa ficar dentro do projeto."
}

New-Item -ItemType Directory -Force -Path $resolvedOutput | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backupFile = Join-Path $resolvedOutput "setup-leitos-$timestamp.sql"

docker compose exec -T db pg_dump `
    --username="${env:POSTGRES_USER}" `
    --dbname="${env:POSTGRES_DB}" `
    --clean --if-exists --no-owner |
    Set-Content -Encoding UTF8 -LiteralPath $backupFile

Write-Output "Backup criado em $backupFile"
