param(
    [string]$OutputDirectory = ".\deploy\releases"
)

$ErrorActionPreference = "Stop"
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$releaseDirectory = [System.IO.Path]::GetFullPath(
    (Join-Path $projectRoot $OutputDirectory)
)

if (-not $releaseDirectory.StartsWith(
    $projectRoot,
    [System.StringComparison]::OrdinalIgnoreCase
)) {
    throw "O pacote precisa ser criado dentro do projeto."
}

New-Item -ItemType Directory -Force -Path $releaseDirectory | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archive = Join-Path $releaseDirectory "setup-leitos-$timestamp.tar.gz"

Push-Location $projectRoot
try {
    tar `
        --exclude=".git" `
        --exclude=".venv" `
        --exclude="backend/.env" `
        --exclude="backend/.env.production" `
        --exclude="backend/*.db" `
        --exclude="backend/*.db-*" `
        --exclude="backend/tests" `
        --exclude="backend/.pytest_cache" `
        --exclude="backend/pytest-cache-files-*" `
        --exclude="pytest-cache-files-*" `
        --exclude="**/__pycache__" `
        --exclude="deploy/backups" `
        --exclude="deploy/certs" `
        --exclude="deploy/releases" `
        -czf $archive `
        backend/app `
        backend/scripts `
        backend/alembic `
        backend/alembic.ini `
        backend/requirements.txt `
        backend/.env.example `
        backend/.env.production.example `
        deploy `
        docs `
        frontend `
        .dockerignore `
        .gitignore `
        docker-compose.yml `
        docker-compose.override.yml `
        Dockerfile `
        README.md
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath $archive -PathType Leaf) {
            Remove-Item -LiteralPath $archive -Force
        }
        throw "Falha ao criar o pacote."
    }
} finally {
    Pop-Location
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash
Write-Output "Pacote criado: $archive"
Write-Output "SHA256: $hash"
