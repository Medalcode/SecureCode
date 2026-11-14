[CmdletBinding()]
param(
    [ValidateRange(1, 500)]
    [int]$Users = 100,
    [ValidateRange(1, 100)]
    [int]$SpawnRate = 10,
    [ValidatePattern('^\d+[smh]$')]
    [string]$Duration = '2m'
)

$ErrorActionPreference = 'Stop'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repositoryRoot

function Assert-PortAvailable([int]$Port) {
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        throw "El puerto local $Port ya está en uso. Cierra el proceso anterior antes de ejecutar esta prueba."
    }
}

function Wait-LocalEndpoint([string]$Url, [string]$Label) {
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        try {
            Invoke-RestMethod -Uri $Url -TimeoutSec 2 | Out-Null
            return
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "$Label no respondió en $Url. Revisa los logs del reporte."
}

Assert-PortAvailable 8000
Assert-PortAvailable 8001

$databasePassword = Read-Host 'Contraseña local de PostgreSQL' -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($databasePassword)
try {
    $encodedPassword = [uri]::EscapeDataString([Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr))
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}

$env:DATABASE_URL = "postgresql+psycopg2://postgres:$encodedPassword@127.0.0.1:5432/securecode_test"
Remove-Variable databasePassword, encodedPassword -ErrorAction SilentlyContinue
$env:PYTHONPATH = 'src'
$env:JWT_SECRET_KEY = 'local-performance-testing-secret-key-2026'
$env:SECURECODE_GITHUB_TEST_MODE = '1'
$env:SECURECODE_GITHUB_TEST_BASE_URL = 'http://127.0.0.1:8001'

$timestamp = Get-Date -Format 'yyyy-MM-dd-HHmmss'
$reportDirectory = Join-Path $repositoryRoot "reports\load-$timestamp"
New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null

$mock = $null
$api = $null
try {
    $mock = Start-Process -FilePath python -ArgumentList 'scripts\mock_github.py' -WorkingDirectory $repositoryRoot -PassThru `
        -RedirectStandardOutput (Join-Path $reportDirectory 'mock.stdout.log') `
        -RedirectStandardError (Join-Path $reportDirectory 'mock.stderr.log')
    Wait-LocalEndpoint 'http://127.0.0.1:8001/__metrics' 'El simulador GitHub local'

    $api = Start-Process -FilePath python -ArgumentList 'scripts\run_perf_api.py' -WorkingDirectory $repositoryRoot -PassThru `
        -RedirectStandardOutput (Join-Path $reportDirectory 'api.stdout.log') `
        -RedirectStandardError (Join-Path $reportDirectory 'api.stderr.log')
    Wait-LocalEndpoint 'http://127.0.0.1:8000/health' 'La API local'

    $csvPrefix = Join-Path $reportDirectory 'locust'
    & locust -f tests\performance\locustfile.py --headless -u $Users -r $SpawnRate -t $Duration `
        --host http://127.0.0.1:8000 --csv $csvPrefix
    $locustExitCode = $LASTEXITCODE

    [ordered]@{
        captured_at_utc = (Get-Date).ToUniversalTime().ToString('o')
        git_commit = (git rev-parse HEAD).Trim()
        users = $Users
        spawn_rate = $SpawnRate
        duration = $Duration
        api_endpoint = 'http://127.0.0.1:8000'
        mock_endpoint = 'http://127.0.0.1:8001'
        database_scope = 'local securecode_test'
        locust_exit_code = $locustExitCode
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $reportDirectory 'run-metadata.json') -Encoding utf8

    if ($locustExitCode -ne 0) {
        throw "Locust terminó con código $locustExitCode. Revisa los CSV y logs en $reportDirectory."
    }
    Write-Host "Prueba completada. Evidencia: $reportDirectory"
}
finally {
    foreach ($process in @($api, $mock)) {
        if ($null -ne $process -and -not $process.HasExited) {
            Stop-Process -Id $process.Id -Force
        }
    }
}
