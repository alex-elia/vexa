# Vexa Production Deployment Script
# This script deploys Vexa Lite to production using Docker

param(
    [string]$Environment = "production",
    [switch]$UseCompose = $false
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Vexa Production Deployment" -ForegroundColor Cyan
Write-Host ""

# Check if .env.production exists
$envFile = ".env.production"
if (-not (Test-Path $envFile)) {
    Write-Host "❌ Error: $envFile not found!" -ForegroundColor Red
    Write-Host "   Please copy .env.production.example to .env.production and fill in your values" -ForegroundColor Yellow
    exit 1
}

# Load environment variables
Write-Host "📋 Loading environment variables from $envFile..." -ForegroundColor Yellow
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        if ($value -match '^\$(.+)$') {
            # Skip variables that reference other variables
            return
        }
        [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
}

# Validate required variables
$requiredVars = @("DATABASE_URL", "ADMIN_API_TOKEN", "TRANSCRIBER_URL", "TRANSCRIBER_API_KEY")
$missingVars = @()

foreach ($var in $requiredVars) {
    $value = [Environment]::GetEnvironmentVariable($var, "Process")
    if (-not $value -or $value -match "your-.*-here" -or $value -match "your_.*") {
        $missingVars += $var
    }
}

if ($missingVars.Count -gt 0) {
    Write-Host "❌ Error: Missing or placeholder values for required variables:" -ForegroundColor Red
    foreach ($var in $missingVars) {
        Write-Host "   - $var" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "Please update $envFile with your actual values" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ All required environment variables are set" -ForegroundColor Green
Write-Host ""

# Check if Docker is running
Write-Host "🐳 Checking Docker..." -ForegroundColor Yellow
try {
    docker info | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Error: Docker is not running!" -ForegroundColor Red
    Write-Host "   Please start Docker Desktop or Docker daemon" -ForegroundColor Yellow
    exit 1
}

# Stop existing container if running
$existingContainer = docker ps -a --filter "name=vexa-production" --format "{{.Names}}"
if ($existingContainer) {
    Write-Host "🛑 Stopping existing container..." -ForegroundColor Yellow
    docker stop vexa-production 2>$null
    docker rm vexa-production 2>$null
    Write-Host "✅ Existing container removed" -ForegroundColor Green
}

if ($UseCompose) {
    Write-Host "📦 Deploying using Docker Compose..." -ForegroundColor Yellow
    docker-compose -f docker-compose.production.yml --env-file .env.production up -d
} else {
    Write-Host "📦 Deploying Vexa Lite container..." -ForegroundColor Yellow
    
    $dbUrl = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
    $dbSslMode = [Environment]::GetEnvironmentVariable("DB_SSL_MODE", "Process")
    $adminToken = [Environment]::GetEnvironmentVariable("ADMIN_API_TOKEN", "Process")
    $transcriberUrl = [Environment]::GetEnvironmentVariable("TRANSCRIBER_URL", "Process")
    $transcriberKey = [Environment]::GetEnvironmentVariable("TRANSCRIBER_API_KEY", "Process")
    
    $dockerArgs = @(
        "run", "-d",
        "--name", "vexa-production",
        "--restart", "unless-stopped",
        "-p", "8056:8056",
        "-e", "DATABASE_URL=$dbUrl",
        "-e", "DB_SSL_MODE=$dbSslMode",
        "-e", "ADMIN_API_TOKEN=$adminToken",
        "-e", "TRANSCRIBER_URL=$transcriberUrl",
        "-e", "TRANSCRIBER_API_KEY=$transcriberKey",
        "vexaai/vexa-lite:latest"
    )
    
    docker @dockerArgs
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Vexa container started successfully" -ForegroundColor Green
    } else {
        Write-Host "❌ Error: Failed to start container" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "⏳ Waiting for service to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if container is running
$containerStatus = docker ps --filter "name=vexa-production" --format "{{.Status}}"
if ($containerStatus) {
    Write-Host "✅ Container is running: $containerStatus" -ForegroundColor Green
} else {
    Write-Host "❌ Error: Container is not running!" -ForegroundColor Red
    Write-Host "   Check logs with: docker logs vexa-production" -ForegroundColor Yellow
    exit 1
}

# Test API endpoint
Write-Host ""
Write-Host "🧪 Testing API endpoint..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8056/docs" -Method Get -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ API is responding" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️  Warning: API endpoint not responding yet (may need more time to start)" -ForegroundColor Yellow
    Write-Host "   Check logs: docker logs vexa-production" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📚 Next steps:" -ForegroundColor Cyan
Write-Host "   1. API Documentation: http://localhost:8056/docs" -ForegroundColor White
Write-Host "   2. Create admin user and API token (see PRODUCTION_DEPLOYMENT.md)" -ForegroundColor White
Write-Host "   3. View logs: docker logs -f vexa-production" -ForegroundColor White
Write-Host "   4. Stop service: docker stop vexa-production" -ForegroundColor White
Write-Host ""
