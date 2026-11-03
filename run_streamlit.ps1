$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
$apiUrl = "http://127.0.0.1:8002"
$streamlitUrl = "http://127.0.0.1:8501"
$apiProcess = $null
$runtimeEnvironment = [Environment]::GetEnvironmentVariable("CROP_PULSE_ENVIRONMENT", "Process")
if ([string]::IsNullOrWhiteSpace($runtimeEnvironment)) { $runtimeEnvironment = "development" }
if ($runtimeEnvironment.Trim().ToLowerInvariant() -in @("staging", "production", "prod")) {
    throw "This local HTTP launcher is for development only. Start staging/production with its HTTPS service configuration."
}
$databaseUrl = [Environment]::GetEnvironmentVariable("CROP_PULSE_DATABASE_URL", "Process")

if (-not (Test-Path -LiteralPath $python)) {
    throw "CropPulse Python environment was not found at $python. Create it and install requirements.txt first."
}
& $python -c "import streamlit, httpx" 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "The project environment is missing Streamlit or httpx. Run .\.venv\Scripts\python.exe -m pip install -r requirements.txt, then retry."
}

if (Get-NetTCPConnection -State Listen -LocalPort 8501 -ErrorAction SilentlyContinue | Select-Object -First 1) {
    throw "Streamlit port 8501 is already in use. Stop the other service before using the React-to-Streamlit single sign-on launcher."
}

function Test-CropPulseApi {
    try {
        $health = Invoke-RestMethod -Uri "$apiUrl/health" -TimeoutSec 2
        $schema = Invoke-RestMethod -Uri "$apiUrl/openapi.json" -TimeoutSec 3
        $paths = $schema.paths.PSObject.Properties.Name
        $csrf = Invoke-WebRequest -Uri "$apiUrl/v1/browser-auth/csrf" -Headers @{ Origin = "http://127.0.0.1:5173" } -TimeoutSec 2
        $csrfPayload = $csrf.Content | ConvertFrom-Json
        $csrfReady = ($csrf.StatusCode -eq 200 -and $csrfPayload.csrf_token.Length -gt 32 `
            -and $csrf.Headers["Access-Control-Allow-Origin"] -eq "http://127.0.0.1:5173")
        return ($health.status -eq "ok" -and $csrfReady -and $paths -contains "/v1/auth/login" -and $paths -contains "/v1/farms" `
            -and $paths -contains "/v1/browser-auth/streamlit-handoff" `
            -and $paths -contains "/v1/streamlit/handoff/exchange" `
            -and $paths -contains "/v1/streamlit/react-handoff" `
            -and $paths -contains "/v1/browser-auth/react-handoff/exchange")
    } catch {
        return $false
    }
}

$listener = Get-NetTCPConnection -State Listen -LocalPort 8002 -ErrorAction SilentlyContinue | Select-Object -First 1
if ($listener) {
    if (-not (Test-CropPulseApi)) {
        throw "Port 8002 is occupied by a service that failed CropPulse readiness checks. No process was stopped. Verify the listener before retrying."
    }
    Write-Host "Using the verified CropPulse API at $apiUrl."
} else {
    if ([string]::IsNullOrWhiteSpace($databaseUrl)) {
        throw "Set CROP_PULSE_DATABASE_URL in the backend launch process before starting a new API. SQLite fallback is disabled."
    }
    $databaseBackend = & $python -c "from backend.db import database_url; from sqlalchemy.engine import make_url; print(make_url(database_url()).get_backend_name())" 2>$null
    if ($LASTEXITCODE -ne 0 -or ($databaseBackend | Select-Object -Last 1) -ne "postgresql") {
        throw "CROP_PULSE_DATABASE_URL must identify a PostgreSQL database using the configured psycopg driver. URL details are omitted."
    }
    $apiSettings = @{
        CROP_PULSE_SECRET_KEY = (& $python -c "import secrets; print(secrets.token_urlsafe(48))").Trim()
        CROP_PULSE_CORS_ORIGINS = "http://127.0.0.1:5173,http://localhost:5173"
        CROP_PULSE_COOKIE_SECURE = "0"
        CROP_PULSE_ENVIRONMENT = $runtimeEnvironment.Trim().ToLowerInvariant()
        CROP_PULSE_AUTO_CREATE_SCHEMA = "0"
        CROP_PULSE_STREAMLIT_URL = $streamlitUrl
    }
    # The explicitly configured PostgreSQL URL is inherited by the API child
    # without being printed or placed on its command line.
    $apiSettings["CROP_PULSE_DATABASE_URL"] = $databaseUrl
    $apiLog = Join-Path $env:TEMP "croppulse-api-8002.log"
    $apiErrorLog = Join-Path $env:TEMP "croppulse-api-8002-error.log"
    $previousSettings = @{}
    try {
        foreach ($name in $apiSettings.Keys) {
            $previousSettings[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
            [Environment]::SetEnvironmentVariable($name, $apiSettings[$name], "Process")
        }
        $apiProcess = Start-Process -FilePath $python `
            -ArgumentList @("-m", "uvicorn", "backend.api:app", "--host", "127.0.0.1", "--port", "8002") `
            -WorkingDirectory $root -WindowStyle Hidden -PassThru `
            -RedirectStandardOutput $apiLog -RedirectStandardError $apiErrorLog
    } finally {
        foreach ($name in $apiSettings.Keys) {
            [Environment]::SetEnvironmentVariable($name, $previousSettings[$name], "Process")
        }
    }

    $ready = $false
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        Start-Sleep -Seconds 1
        if (Test-CropPulseApi) {
            $ready = $true
            if ($apiProcess.HasExited) { $apiProcess = $null }
            break
        }
        if ($apiProcess.HasExited) { break }
    }
    if (-not $ready) {
        if ($apiProcess -and -not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id -Force }
        if (Test-Path -LiteralPath $apiErrorLog) { Get-Content -LiteralPath $apiErrorLog -Tail 30 }
        throw "The CropPulse API did not become ready. Check the API error log at $apiErrorLog."
    }
    Write-Host "CropPulse API is ready at $apiUrl."
}

$serverOnlySettings = @(
    "CROP_PULSE_DATABASE_URL", "CROP_PULSE_SECRET_KEY", "CROP_PULSE_CORS_ORIGINS",
    "CROP_PULSE_COOKIE_SECURE", "CROP_PULSE_ENVIRONMENT", "CROP_PULSE_AUTO_CREATE_SCHEMA",
    "CROP_PULSE_STREAMLIT_URL"
)
$streamlitParentValues = @{}
foreach ($name in $serverOnlySettings) {
    $streamlitParentValues[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
    [Environment]::SetEnvironmentVariable($name, $null, "Process")
}
$env:CROP_PULSE_API_URL = $apiUrl
Write-Host "Starting Streamlit. Open the URL printed by Streamlit below (normally http://127.0.0.1:8501)."
try {
    & $python -m streamlit run (Join-Path $root "app.py") --server.address 127.0.0.1 --server.port 8501
} finally {
    foreach ($name in $serverOnlySettings) {
        [Environment]::SetEnvironmentVariable($name, $streamlitParentValues[$name], "Process")
    }
    if ($apiProcess -and -not $apiProcess.HasExited) {
        Stop-Process -Id $apiProcess.Id -Force
    }
}
