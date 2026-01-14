# Vexa Production Quick Start

Get Vexa running in production in 5 minutes.

## Prerequisites

- Docker installed and running
- Supabase account (or any PostgreSQL database)
- Transcription API key (from https://staging.vexa.ai/dashboard/transcription)

## Step 1: Set Up Environment

```powershell
# Copy the example environment file
Copy-Item .env.production.example .env.production

# Edit .env.production and fill in:
# - DATABASE_URL (from Supabase)
# - ADMIN_API_TOKEN (generate with: openssl rand -hex 32)
# - TRANSCRIBER_API_KEY (from Vexa dashboard)
```

## Step 2: Deploy

```powershell
# Run the deployment script
.\scripts\deploy-production.ps1
```

Or manually:

```powershell
docker run -d `
  --name vexa-production `
  --restart unless-stopped `
  -p 8056:8056 `
  --env-file .env.production `
  vexaai/vexa-lite:latest
```

## Step 3: Create Admin User

```powershell
.\scripts\create-admin-user.ps1 `
  -Email "admin@yourcompany.com" `
  -Name "Admin User" `
  -AdminToken "your-admin-token-from-env"
```

## Step 4: Test

```powershell
# Check API docs
Start-Process "http://localhost:8056/docs"

# Test API with your token
$token = Get-Content "vexa-api-token-admin@yourcompany.com.txt" | Select-String "API Token:" | ForEach-Object { $_.Line.Split(':')[1].Trim() }
curl -H "X-API-Key: $token" "http://localhost:8056/meetings"
```

## Next Steps

- See [PRODUCTION_DEPLOYMENT.md](./PRODUCTION_DEPLOYMENT.md) for detailed documentation
- See [docs/self-hosted-management.md](./docs/self-hosted-management.md) for user management
- Integrate with Nemrut app
