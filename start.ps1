[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [ValidateRange(0, 3600)]
    [int]$AutoStopSeconds = 0
)

$ErrorActionPreference = "Stop"
$projectRoot = $PSScriptRoot
$backendRoot = Join-Path $projectRoot "backend"
$frontendRoot = Join-Path $projectRoot "frontend"
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$frontendUrl = "http://127.0.0.1:5173"
$healthUrl = "http://127.0.0.1:8000/api/v1/health"
$startedAt = Get-Date
$startedProcesses = @()
$ownedListenerIds = @()

function Test-LocalPort {
    param([int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $result = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $result.AsyncWaitHandle.WaitOne(250)) {
            return $false
        }
        $client.EndConnect($result)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Get-PnpmCommand {
    $pnpm = Get-Command "pnpm.cmd" -ErrorAction SilentlyContinue
    if (-not $pnpm) {
        $pnpm = Get-Command "pnpm" -ErrorAction SilentlyContinue
    }
    if ($pnpm) {
        return [pscustomobject]@{
            FilePath = $pnpm.Source
            Arguments = @("dev", "--host", "127.0.0.1")
        }
    }

    $corepack = Get-Command "corepack.cmd" -ErrorAction SilentlyContinue
    if (-not $corepack) {
        $corepack = Get-Command "corepack" -ErrorAction SilentlyContinue
    }
    if ($corepack) {
        return [pscustomobject]@{
            FilePath = $corepack.Source
            Arguments = @("pnpm", "dev", "--host", "127.0.0.1")
        }
    }

    throw "pnpm was not found. Install Node.js and pnpm first."
}

function Add-NodeToPath {
    if (Get-Command "node.exe" -ErrorAction SilentlyContinue) {
        return
    }

    $pnpmCommand = Get-Command "pnpm.cmd" -ErrorAction SilentlyContinue
    if (-not $pnpmCommand) {
        return
    }

    $runtimeRoot = Split-Path (Split-Path (Split-Path $pnpmCommand.Source -Parent) -Parent) -Parent
    $nodeDirectory = Join-Path $runtimeRoot "node\bin"
    if (Test-Path -LiteralPath (Join-Path $nodeDirectory "node.exe")) {
        $env:PATH = "$nodeDirectory;$env:PATH"
    }
}

function Wait-ForReadMaster {
    param([int]$TimeoutSeconds = 45)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        foreach ($process in $startedProcesses) {
            if ($process.HasExited) {
                throw "A ReadMaster service exited before startup completed."
            }
        }

        try {
            $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
            $frontend = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2
            if ($health.status -eq "ok" -and $frontend.StatusCode -eq 200) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "ReadMaster did not become ready within $TimeoutSeconds seconds."
}

function Remember-ListenerProcesses {
    foreach ($port in @(8000, 5173)) {
        $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($connection in $connections) {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            if ($process -and $process.StartTime -ge $startedAt.AddSeconds(-2)) {
                $script:ownedListenerIds += $process.Id
            }
        }
    }
    $script:ownedListenerIds = @($script:ownedListenerIds | Sort-Object -Unique)
}

function Stop-ReadMaster {
    Write-Host "`nStopping ReadMaster..." -ForegroundColor Yellow

    foreach ($processId in $ownedListenerIds) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
    }
    foreach ($process in $startedProcesses) {
        if (-not $process.HasExited) {
            Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

try {
    Write-Host "ReadMaster one-click startup" -ForegroundColor Cyan
    Write-Host "Project: $projectRoot"

    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw "Python environment not found: $pythonPath`nRun the installation steps in README.md first."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $frontendRoot "node_modules"))) {
        throw "Frontend dependencies are missing. Run 'pnpm install' in the frontend folder first."
    }
    if (Test-LocalPort 8000) {
        throw "Port 8000 is already in use. Stop the existing backend service and try again."
    }
    if (Test-LocalPort 5173) {
        throw "Port 5173 is already in use. Stop the existing frontend service and try again."
    }

    Add-NodeToPath
    $pnpmCommand = Get-PnpmCommand
    if (-not (Get-Command "node.exe" -ErrorAction SilentlyContinue)) {
        throw "node.exe was not found. Install Node.js 22 or newer and try again."
    }
    Write-Host "Starting backend..." -ForegroundColor Green
    $backendProcess = Start-Process `
        -FilePath $pythonPath `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000") `
        -WorkingDirectory $backendRoot `
        -NoNewWindow `
        -PassThru
    $startedProcesses += $backendProcess

    Write-Host "Starting frontend..." -ForegroundColor Green
    $frontendProcess = Start-Process `
        -FilePath $pnpmCommand.FilePath `
        -ArgumentList $pnpmCommand.Arguments `
        -WorkingDirectory $frontendRoot `
        -NoNewWindow `
        -PassThru
    $startedProcesses += $frontendProcess

    Write-Host "Waiting for services..."
    Wait-ForReadMaster
    Remember-ListenerProcesses

    Write-Host "`nReadMaster is ready." -ForegroundColor Green
    Write-Host "Application: $frontendUrl"
    Write-Host "API docs:    http://127.0.0.1:8000/docs"

    if (-not $NoBrowser) {
        Start-Process $frontendUrl
    }

    if ($AutoStopSeconds -gt 0) {
        Write-Host "Automatic stop in $AutoStopSeconds seconds."
        Start-Sleep -Seconds $AutoStopSeconds
    }
    else {
        Read-Host "Press Enter to stop ReadMaster"
    }
}
catch {
    Write-Host "`nStartup failed: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
finally {
    Stop-ReadMaster
}
