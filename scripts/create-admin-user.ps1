# Script to create admin user and API token for Vexa
# Usage: .\create-admin-user.ps1 -Email "admin@example.com" -Name "Admin User" -AdminToken "your-admin-token"

param(
    [Parameter(Mandatory=$true)]
    [string]$Email,
    
    [Parameter(Mandatory=$false)]
    [string]$Name = "Admin User",
    
    [Parameter(Mandatory=$false)]
    [int]$MaxConcurrentBots = 10,
    
    [Parameter(Mandatory=$false)]
    [string]$AdminToken = "token",
    
    [Parameter(Mandatory=$false)]
    [string]$BaseUrl = "http://localhost:8056"
)

$ErrorActionPreference = "Stop"

Write-Host "👤 Creating Vexa Admin User" -ForegroundColor Cyan
Write-Host ""

# Step 1: Create user
Write-Host "📝 Creating user: $Email" -ForegroundColor Yellow

$userBody = @{
    email = $Email
    name = $Name
    max_concurrent_bots = $MaxConcurrentBots
} | ConvertTo-Json

try {
    $userResponse = Invoke-RestMethod -Uri "$BaseUrl/admin/users" `
        -Method Post `
        -Headers @{
            "Content-Type" = "application/json"
            "X-Admin-API-Key" = $AdminToken
        } `
        -Body $userBody
    
    $userId = $userResponse.id
    Write-Host "✅ User created successfully (ID: $userId)" -ForegroundColor Green
    Write-Host "   Email: $($userResponse.email)" -ForegroundColor Gray
    Write-Host "   Name: $($userResponse.name)" -ForegroundColor Gray
    Write-Host "   Max Concurrent Bots: $($userResponse.max_concurrent_bots)" -ForegroundColor Gray
    Write-Host ""
} catch {
    if ($_.Exception.Response.StatusCode -eq 409) {
        Write-Host "⚠️  User already exists, retrieving existing user..." -ForegroundColor Yellow
        
        # Get user by email
        $encodedEmail = [System.Web.HttpUtility]::UrlEncode($Email)
        $userResponse = Invoke-RestMethod -Uri "$BaseUrl/admin/users/email/$encodedEmail" `
            -Method Get `
            -Headers @{
                "X-Admin-API-Key" = $AdminToken
            }
        
        $userId = $userResponse.id
        Write-Host "✅ Found existing user (ID: $userId)" -ForegroundColor Green
        Write-Host ""
    } else {
        Write-Host "❌ Error creating user: $_" -ForegroundColor Red
        exit 1
    }
}

# Step 2: Create API token
Write-Host "🔑 Generating API token..." -ForegroundColor Yellow

try {
    $tokenResponse = Invoke-RestMethod -Uri "$BaseUrl/admin/users/$userId/tokens" `
        -Method Post `
        -Headers @{
            "X-Admin-API-Key" = $AdminToken
        }
    
    $apiToken = $tokenResponse.token
    Write-Host "✅ API token generated successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host "⚠️  IMPORTANT: Save this API token - it cannot be retrieved later!" -ForegroundColor Yellow
    Write-Host "=" * 60 -ForegroundColor Cyan
    Write-Host ""
    Write-Host "API Token: $apiToken" -ForegroundColor White -BackgroundColor DarkGreen
    Write-Host ""
    Write-Host "Usage example:" -ForegroundColor Cyan
    Write-Host "  curl -H `"X-API-Key: $apiToken`" `"$BaseUrl/meetings`"" -ForegroundColor Gray
    Write-Host ""
    
    # Save to file
    $tokenFile = "vexa-api-token-$Email.txt"
    @"
Vexa API Token
==============
Email: $Email
User ID: $userId
API Token: $apiToken
Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

Usage:
  curl -H "X-API-Key: $apiToken" "$BaseUrl/meetings"
"@ | Out-File -FilePath $tokenFile -Encoding UTF8
    
    Write-Host "💾 Token saved to: $tokenFile" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "❌ Error generating API token: $_" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Setup complete!" -ForegroundColor Green
