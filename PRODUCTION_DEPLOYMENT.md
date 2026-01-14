# Vexa Production Deployment Guide

This guide covers deploying Vexa to production for your own use and for your clients.

## Deployment Options

### Option 1: Vexa Lite (Recommended for Production)
- **Single container** - Easy to deploy and manage
- **No GPU required** - Uses external transcription service
- **Stateless** - All data in database, easy to scale
- **Best for**: Production deployments, serverless, Kubernetes

### Option 2: Full Stack (Docker Compose)
- **Multiple services** - More control, more complex
- **GPU or CPU** - Can self-host transcription
- **Best for**: Development, on-premise deployments

## Quick Start: Vexa Lite Production Deployment

### Prerequisites

1. **Database**: PostgreSQL (Supabase recommended for production)
2. **Transcription Service**: 
   - Option A: Use hosted transcription service (get API key from https://staging.vexa.ai/dashboard/transcription)
   - Option B: Self-host transcription service (requires GPU)

### Step 1: Set Up Database

#### Using Supabase (Recommended)

1. Create a new Supabase project at [supabase.com](https://supabase.com)
2. Go to **Settings** → **Database**
3. Copy the **Connection string** (Session pooler mode)
4. Format: `postgresql://postgres.your_project_id:[YOUR-PASSWORD]@aws-0-us-west-2.pooler.supabase.com:5432/postgres`

#### Using Remote PostgreSQL

Use any PostgreSQL database with connection string:
```
postgresql://user:password@host:5432/vexa
```

### Step 2: Get Transcription Service

#### Option A: Hosted Transcription (Easiest)

1. Get API key from: https://staging.vexa.ai/dashboard/transcription
2. Transcription URL: `https://transcription.vexa.ai/v1/audio/transcriptions`

#### Option B: Self-Host Transcription

See `services/transcription-service/README.md` for setup instructions.

### Step 3: Deploy Vexa Lite

#### Using Docker (Quick Start)

```bash
docker run -d \
  --name vexa \
  -p 8056:8056 \
  -e DATABASE_URL="postgresql://postgres.your_project_id:password@aws-0-us-west-2.pooler.supabase.com:5432/postgres" \
  -e DB_SSL_MODE="require" \
  -e ADMIN_API_TOKEN="your-secure-admin-token-here" \
  -e TRANSCRIBER_URL="https://transcription.vexa.ai/v1/audio/transcriptions" \
  -e TRANSCRIBER_API_KEY="your-transcription-api-key" \
  vexaai/vexa-lite:latest
```

#### Using Docker Compose

See `docker-compose.production.yml` in this directory.

#### Using Kubernetes

See `k8s/deployment-vexa.yaml` in this directory.

### Step 4: Verify Deployment

```bash
# Check if container is running
docker ps | grep vexa

# Check logs
docker logs vexa

# Test API
curl http://localhost:8056/docs
```

### Step 5: Create Admin User and API Token

```bash
# Create a user
curl -X POST http://localhost:8056/admin/users \
  -H "Content-Type: application/json" \
  -H "X-Admin-API-Key: your-secure-admin-token-here" \
  -d '{
    "email": "admin@yourcompany.com",
    "name": "Admin User",
    "max_concurrent_bots": 10
  }'

# Note the user ID from response, then create API token
curl -X POST http://localhost:8056/admin/users/1/tokens \
  -H "X-Admin-API-Key: your-secure-admin-token-here"
```

**⚠️ Save the API token immediately - it cannot be retrieved later!**

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@host:5432/vexa` |
| `ADMIN_API_TOKEN` | Yes | Secret token for admin operations | `your-secure-admin-token` |
| `TRANSCRIBER_URL` | Yes | Transcription service endpoint | `https://transcription.vexa.ai/v1/audio/transcriptions` |
| `TRANSCRIBER_API_KEY` | Yes | API key for transcription service | `your-api-key` |
| `DB_SSL_MODE` | Optional | SSL mode for database (use `require` for Supabase) | `require` |

## Production Best Practices

1. **Use Strong Admin Token**: Generate a secure random token for `ADMIN_API_TOKEN`
2. **Use Remote Database**: Don't use local database for production
3. **Enable SSL**: Always use SSL for database connections in production
4. **Monitor Logs**: Set up log aggregation (e.g., CloudWatch, Datadog)
5. **Backup Database**: Regular backups of your PostgreSQL database
6. **Rate Limiting**: Consider adding rate limiting at ingress/load balancer level
7. **Health Checks**: Use `/health` endpoint for monitoring

## Scaling

Vexa Lite is stateless and can be scaled horizontally:

```bash
# Run multiple instances behind a load balancer
docker run -d --name vexa-1 -p 8056:8056 ... vexaai/vexa-lite:latest
docker run -d --name vexa-2 -p 8057:8056 ... vexaai/vexa-lite:latest
docker run -d --name vexa-3 -p 8058:8056 ... vexaai/vexa-lite:latest
```

## Troubleshooting

### Container won't start
- Check database connection string
- Verify transcription service URL and API key
- Check logs: `docker logs vexa`

### Database connection errors
- Verify `DATABASE_URL` is correct
- For Supabase, ensure `DB_SSL_MODE=require`
- Check database firewall rules

### Transcription not working
- Verify `TRANSCRIBER_URL` and `TRANSCRIBER_API_KEY`
- Check transcription service is accessible
- Review transcription service logs

## Next Steps

- [User Management Guide](docs/self-hosted-management.md)
- [API Documentation](http://localhost:8056/docs)
- [Integration with Nemrut](../nemrut/README.md)
