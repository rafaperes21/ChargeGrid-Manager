<#
.SYNOPSIS
    Sobe o ambiente de desenvolvimento do ChargeGrid-Manager com um unico comando.

.DESCRIPTION
    Garante os .env de cada servico, sobe o Postgres via docker compose, cria/instala os
    venvs (Python 3.11) e node_modules que faltarem, roda migration+seed+gerador de historico
    no backend, e abre cada servico numa janela de terminal separada.

    E idempotente: pode rodar de novo a qualquer momento sem duplicar dado ou reinstalar do
    zero (seed e gerador de historico ja se protegem sozinhos; o script pula venv/node_modules
    que ja existem).

.PARAMETER Only
    Lista de servicos a considerar. Default: todos (backend, ia, frontend-proprietario,
    frontend-cliente). Ex.: -Only backend,ia (util para o video da IA, sem os frontends).

.PARAMETER SkipSetup
    Pula instalacao/migrations/seed/gerador - so abre as janelas dos servicos. Uso do dia a
    dia depois do primeiro `dev.ps1`.

.PARAMETER Recreate
    Apaga e recria os .venv/node_modules antes de instalar. Use se um venv ficar com a versao
    errada de Python ou dependencias quebradas.

.EXAMPLE
    .\scripts\dev.ps1

.EXAMPLE
    .\scripts\dev.ps1 -Only backend,ia

.EXAMPLE
    .\scripts\dev.ps1 -SkipSetup
#>
[CmdletBinding()]
param(
    [string[]]$Only = @('backend', 'ia', 'frontend-proprietario', 'frontend-cliente'),
    [switch]$SkipSetup,
    [switch]$Recreate
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$allServiceNames = @('backend', 'ia', 'frontend-proprietario', 'frontend-cliente')
$postgresUser = 'chargegrid'  # precisa bater com POSTGRES_USER do .env.example da raiz

foreach ($name in $Only) {
    if ($allServiceNames -notcontains $name) {
        Write-Error "Servico desconhecido: '$name'. Use um de: $($allServiceNames -join ', ')"
        exit 1
    }
}

function Ensure-Env([string]$dir) {
    $example = Join-Path $dir '.env.example'
    $envFile = Join-Path $dir '.env'
    if ((Test-Path $example) -and -not (Test-Path $envFile)) {
        Copy-Item $example $envFile
        Write-Host "  .env criado em $dir"
    }
}

function Ensure-PythonVenv([string]$dir) {
    $venvPath = Join-Path $dir '.venv'
    if ($Recreate -and (Test-Path $venvPath)) {
        Write-Host "  Removendo venv existente em $dir..."
        Remove-Item -Recurse -Force $venvPath
    }
    if (-not (Test-Path $venvPath)) {
        Write-Host "  Criando venv (Python 3.11) em $dir..."
        py -3.11 -m venv $venvPath
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Nao encontrei Python 3.11 (comando 'py -3.11'). Instale o Python 3.11 e tente de novo - versoes mais novas quebram o Prophet/cmdstanpy da IA."
            exit 1
        }
    }
    return (Join-Path $venvPath 'Scripts\python.exe')
}

function Install-Requirements([string]$dir, [string]$pythonExe) {
    Write-Host "  Instalando dependencias em $dir..."
    & $pythonExe -m pip install --upgrade pip -q
    & $pythonExe -m pip install -q -r (Join-Path $dir 'requirements-dev.txt')
    if ($LASTEXITCODE -ne 0) {
        Write-Error "pip install falhou em $dir."
        exit 1
    }
}

function Ensure-NodeModules([string]$dir) {
    $nodeModules = Join-Path $dir 'node_modules'
    if ($Recreate -and (Test-Path $nodeModules)) {
        Write-Host "  Removendo node_modules existente em $dir..."
        Remove-Item -Recurse -Force $nodeModules
    }
    if (-not (Test-Path $nodeModules)) {
        Write-Host "  Rodando npm install em $dir..."
        Push-Location $dir
        try { npm install } finally { Pop-Location }
        if ($LASTEXITCODE -ne 0) {
            Write-Error "npm install falhou em $dir."
            exit 1
        }
    }
}

function Wait-Postgres {
    Write-Host "  Aguardando Postgres ficar saudavel..."
    $maxAttempts = 30
    for ($i = 1; $i -le $maxAttempts; $i++) {
        docker compose exec -T postgres pg_isready -U $postgresUser *> $null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Postgres pronto."
            return
        }
        Start-Sleep -Seconds 2
    }
    Write-Error "Postgres nao respondeu em $($maxAttempts * 2)s. Confira se o Docker Desktop esta rodando ('docker ps') e tente 'docker compose up -d' manualmente."
    exit 1
}

function Start-ServiceWindow([string]$title, [string]$workDir, [string]$command) {
    $fullDir = Join-Path $root $workDir
    $inner = "`$Host.UI.RawUI.WindowTitle = '$title'; Set-Location '$fullDir'; $command"
    Start-Process powershell -ArgumentList '-NoExit', '-Command', $inner | Out-Null
    Write-Host "  Aberto: $title"
}

Write-Host "=== ChargeGrid-Manager dev ==="
Write-Host "Servicos: $($Only -join ', ')"

Write-Host "`n[1/4] Conferindo .env..."
Ensure-Env $root
foreach ($name in $allServiceNames) {
    Ensure-Env (Join-Path $root $name)
}

$needsPostgres = ($Only -contains 'backend') -or ($Only -contains 'ia')
if ($needsPostgres) {
    Write-Host "`n[2/4] Subindo Postgres..."
    Push-Location $root
    try {
        docker compose up -d
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Falha ao rodar 'docker compose up -d'. O Docker Desktop esta rodando?"
            exit 1
        }
        Wait-Postgres
    } finally {
        Pop-Location
    }
} else {
    Write-Host "`n[2/4] Postgres nao necessario para os servicos escolhidos - pulando."
}

if (-not $SkipSetup) {
    Write-Host "`n[3/4] Setup dos servicos..."

    if ($Only -contains 'backend') {
        Write-Host "backend:"
        $backendDir = Join-Path $root 'backend'
        $backendPy = Ensure-PythonVenv $backendDir
        Install-Requirements $backendDir $backendPy

        Push-Location $backendDir
        try {
            Write-Host "  Rodando migrations..."
            & $backendPy -m alembic upgrade head
            if ($LASTEXITCODE -ne 0) { Write-Error "alembic upgrade head falhou."; exit 1 }

            Write-Host "  Rodando seed..."
            & $backendPy -m app.db.seed

            Write-Host "  Rodando gerador de historico (pode levar alguns segundos)..."
            & $backendPy -m simulador.historical_generator --seed 42
        } finally {
            Pop-Location
        }
    }

    if ($Only -contains 'ia') {
        Write-Host "ia:"
        $iaDir = Join-Path $root 'ia'
        $iaPy = Ensure-PythonVenv $iaDir
        Install-Requirements $iaDir $iaPy
    }

    foreach ($frontend in @('frontend-proprietario', 'frontend-cliente')) {
        if ($Only -contains $frontend) {
            Write-Host "${frontend}:"
            Ensure-NodeModules (Join-Path $root $frontend)
        }
    }
} else {
    Write-Host "`n[3/4] -SkipSetup: pulando instalacao/migrations/seed/gerador."
}

Write-Host "`n[4/4] Abrindo servicos..."

if ($Only -contains 'backend') {
    $backendPy = Join-Path $root 'backend\.venv\Scripts\python.exe'
    Start-ServiceWindow 'ChargeGrid - backend' 'backend' "& '$backendPy' -m uvicorn app.main:app --reload --port 8000"
}
if ($Only -contains 'ia') {
    $iaPy = Join-Path $root 'ia\.venv\Scripts\python.exe'
    Start-ServiceWindow 'ChargeGrid - ia' 'ia' "& '$iaPy' -m uvicorn app.main:app --reload --port 8001"
}
if ($Only -contains 'frontend-proprietario') {
    Start-ServiceWindow 'ChargeGrid - portal proprietario' 'frontend-proprietario' 'npm run dev'
}
if ($Only -contains 'frontend-cliente') {
    Start-ServiceWindow 'ChargeGrid - portal cliente' 'frontend-cliente' 'npm run dev'
}

Write-Host "`nPronto. URLs:"
if ($Only -contains 'backend') { Write-Host "  backend:      http://localhost:8000/docs" }
if ($Only -contains 'ia') { Write-Host "  ia:           http://localhost:8001/docs" }
if ($Only -contains 'frontend-proprietario') { Write-Host "  proprietario: veja a porta na janela aberta (Vite, geralmente 5173)" }
if ($Only -contains 'frontend-cliente') { Write-Host "  cliente:      veja a porta na janela aberta (Vite, geralmente 5174)" }
