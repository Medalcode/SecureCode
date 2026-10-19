if (-not $env:DATABASE_URL) {
    throw "DATABASE_URL debe configurarse antes de ejecutar Locust."
}

if ($env:DATABASE_URL -notmatch '/securecode_test(?:\?|$)') {
    throw "Solo se permite ejecutar contra securecode_test."
}

if ($env:DATABASE_URL -notmatch '@(?:localhost|127\.0\.0\.1):5432/') {
    throw "Solo se permite PostgreSQL local en el puerto 5432."
}
$env:GITHUB_API_BASE_URL="http://localhost:8001"
$env:PYTHONPATH="src"
$env:JWT_SECRET_KEY="test-secret-key-that-is-at-least-32-bytes-long"

Write-Host "Iniciando Pruebas de Rendimiento ES2..."

Write-Host "`n[Escenario 1] Carga Nominal: 5 usuarios, 2 min, r=1"
locust -f tests/performance/locustfile.py --headless -u 5 -r 1 -t 2m --host=http://127.0.0.1:8000 --csv=reports/nominal_load

Write-Host "`n[Escenario 2] Concurrencia Progresiva - Nivel 1: 10 usuarios, 1 min, r=2"
locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 1m --host=http://127.0.0.1:8000 --csv=reports/progressive_10

Write-Host "`n[Escenario 2] Concurrencia Progresiva - Nivel 2: 20 usuarios, 1 min, r=2"
locust -f tests/performance/locustfile.py --headless -u 20 -r 2 -t 1m --host=http://127.0.0.1:8000 --csv=reports/progressive_20

Write-Host "`n[Escenario 2] Concurrencia Progresiva - Nivel 3: 30 usuarios, 1 min, r=2"
locust -f tests/performance/locustfile.py --headless -u 30 -r 2 -t 1m --host=http://127.0.0.1:8000 --csv=reports/progressive_30

Write-Host "`n[Escenario 3] Estres Controlado: 50 usuarios, 2 min, r=5"
locust -f tests/performance/locustfile.py --headless -u 50 -r 5 -t 2m --host=http://127.0.0.1:8000 --csv=reports/stress_load

Write-Host "`nPruebas finalizadas con exito."
