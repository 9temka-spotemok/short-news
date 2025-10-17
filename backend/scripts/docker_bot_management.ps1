# Telegram Bot Docker Management Script for Windows PowerShell
# This script helps manage the Telegram bot Docker container on Windows

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "restart", "logs", "status", "build", "shell", "health", "setup", "clean")]
    [string]$Command
)

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Function to check if docker is available
function Test-Docker {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Error "Docker is not installed or not in PATH!"
        exit 1
    }
    
    # Check if docker compose is available
    if (docker compose version 2>$null) {
        $script:ComposeCommand = "docker compose"
    } elseif (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $script:ComposeCommand = "docker-compose"
    } else {
        Write-Error "Neither 'docker compose' nor 'docker-compose' is available!"
        exit 1
    }
}

# Function to get project root directory
function Get-ProjectRoot {
    $scriptPath = Split-Path -Parent $MyInvocation.PSCommandPath
    return Split-Path -Parent (Split-Path -Parent $scriptPath)
}

# Function to start the bot
function Start-Bot {
    Write-Status "Starting Telegram bot container..."
    
    $projectRoot = Get-ProjectRoot
    Set-Location $projectRoot
    
    Invoke-Expression "$ComposeCommand up -d telegram-bot"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Telegram bot container started successfully!"
        Write-Status "Use '$Command logs' to view logs"
        Write-Status "Use '$Command status' to check status"
    } else {
        Write-Error "Failed to start telegram bot container!"
        exit 1
    }
}

# Function to stop the bot
function Stop-Bot {
    Write-Status "Stopping Telegram bot container..."
    
    $projectRoot = Get-ProjectRoot
    Set-Location $projectRoot
    
    Invoke-Expression "$ComposeCommand stop telegram-bot"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Telegram bot container stopped successfully!"
    } else {
        Write-Error "Failed to stop telegram bot container!"
        exit 1
    }
}

# Function to restart the bot
function Restart-Bot {
    Write-Status "Restarting Telegram bot container..."
    
    $projectRoot = Get-ProjectRoot
    Set-Location $projectRoot
    
    Invoke-Expression "$ComposeCommand restart telegram-bot"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Telegram bot container restarted successfully!"
    } else {
        Write-Error "Failed to restart telegram bot container!"
        exit 1
    }
}

# Function to show logs
function Show-Logs {
    Write-Status "Showing Telegram bot logs (Ctrl+C to exit)..."
    
    $projectRoot = Get-ProjectRoot
    Set-Location $projectRoot
    
    Invoke-Expression "$ComposeCommand logs -f telegram-bot"
}

# Function to show status
function Show-Status {
    Write-Status "Telegram bot container status:"
    
    $projectRoot = Get-ProjectRoot
    Set-Location $projectRoot
    
    Invoke-Expression "$ComposeCommand ps telegram-bot"
    
    Write-Host ""
    Write-Status "Container health:"
    
    try {
        $healthStatus = docker inspect shot-news-telegram-bot --format='{{.State.Health.Status}}' 2>$null
        if ($healthStatus) {
            Write-Host $healthStatus
        } else {
            Write-Host "No health check available"
        }
    } catch {
        Write-Host "Health check not available"
    }
}

# Function to build the bot image
function Build-Bot {
    Write-Status "Building Telegram bot Docker image..."
    
    $projectRoot = Get-ProjectRoot
    Set-Location $projectRoot
    
    Invoke-Expression "$ComposeCommand build telegram-bot"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Telegram bot image built successfully!"
    } else {
        Write-Error "Failed to build telegram bot image!"
        exit 1
    }
}

# Function to open shell in container
function Open-Shell {
    Write-Status "Opening shell in Telegram bot container..."
    
    docker exec -it shot-news-telegram-bot /bin/bash
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Shell session ended"
    } else {
        Write-Error "Failed to open shell in container!"
        exit 1
    }
}

# Function to check bot health
function Test-BotHealth {
    Write-Status "Checking Telegram bot health..."
    
    # Check if container is running
    $containerRunning = docker ps --format "table {{.Names}}" | Select-String "shot-news-telegram-bot"
    
    if (-not $containerRunning) {
        Write-Error "Telegram bot container is not running!"
        exit 1
    }
    
    # Check container health
    try {
        $healthStatus = docker inspect shot-news-telegram-bot --format='{{.State.Health.Status}}' 2>$null
        
        if ($healthStatus -eq "healthy") {
            Write-Success "Telegram bot is healthy!"
        } elseif ($healthStatus -eq "unhealthy") {
            Write-Error "Telegram bot is unhealthy!"
            Write-Status "Check logs with: $Command logs"
            exit 1
        } else {
            Write-Warning "Health check status: $healthStatus"
        }
    } catch {
        Write-Warning "Health check not available"
    }
    
    # Test bot API
    Write-Status "Testing bot API connection..."
    
    # Get bot token from environment
    $botToken = docker exec shot-news-telegram-bot printenv TELEGRAM_BOT_TOKEN 2>$null
    
    if (-not $botToken) {
        Write-Error "TELEGRAM_BOT_TOKEN not found in container!"
        exit 1
    }
    
    # Test API call
    try {
        $response = Invoke-RestMethod -Uri "https://api.telegram.org/bot$botToken/getMe" -Method Get
        
        if ($response.ok) {
            Write-Success "Bot API connection successful!"
            Write-Host "  Bot name: $($response.result.first_name)"
            Write-Host "  Bot username: @$($response.result.username)"
        } else {
            Write-Error "Bot API connection failed!"
            Write-Host "Response: $($response | ConvertTo-Json)"
            exit 1
        }
    } catch {
        Write-Error "Bot API connection failed!"
        Write-Host "Error: $($_.Exception.Message)"
        exit 1
    }
}

# Function to setup bot configuration
function Setup-Bot {
    Write-Status "Setting up Telegram bot configuration..."
    
    $projectRoot = Get-ProjectRoot
    $envFile = Join-Path $projectRoot "backend\.env"
    $envExampleFile = Join-Path $projectRoot "backend\env.example"
    
    # Check if .env file exists
    if (-not (Test-Path $envFile)) {
        Write-Warning ".env file not found, creating from example..."
        if (Test-Path $envExampleFile) {
            Copy-Item $envExampleFile $envFile
            Write-Status "Please edit backend\.env file with your configuration"
        } else {
            Write-Error "env.example file not found!"
            exit 1
        }
    }
    
    # Run the interactive setup script
    Write-Status "Running interactive bot setup..."
    
    $backendDir = Join-Path $projectRoot "backend"
    Set-Location $backendDir
    
    python setup_telegram_bot_interactive.py
    
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Bot setup completed!"
        Write-Status "You can now start the bot with: $Command start"
    } else {
        Write-Error "Bot setup failed!"
        exit 1
    }
}

# Function to clean up
function Clear-BotResources {
    Write-Status "Cleaning up Telegram bot containers and images..."
    
    $projectRoot = Get-ProjectRoot
    Set-Location $projectRoot
    
    # Stop and remove container
    Invoke-Expression "$ComposeCommand stop telegram-bot" 2>$null
    Invoke-Expression "$ComposeCommand rm -f telegram-bot" 2>$null
    
    # Remove image
    $imageId = docker images --format "{{.Repository}}:{{.Tag}} {{.ID}}" | Where-Object { $_ -match "shot-news.*telegram-bot" } | ForEach-Object { ($_ -split " ")[1] }
    if ($imageId) {
        docker rmi $imageId 2>$null
    }
    
    Write-Success "Cleanup completed!"
}

# Main script logic
function Main {
    Test-Docker
    
    switch ($Command) {
        "start" { Start-Bot }
        "stop" { Stop-Bot }
        "restart" { Restart-Bot }
        "logs" { Show-Logs }
        "status" { Show-Status }
        "build" { Build-Bot }
        "shell" { Open-Shell }
        "health" { Test-BotHealth }
        "setup" { Setup-Bot }
        "clean" { Clear-BotResources }
    }
}

# Show usage if no command provided
if (-not $Command) {
    Write-Host "Telegram Bot Docker Management Script for Windows"
    Write-Host "Usage: .\docker_bot_management.ps1 [COMMAND]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start     - Start the telegram bot container"
    Write-Host "  stop      - Stop the telegram bot container"
    Write-Host "  restart   - Restart the telegram bot container"
    Write-Host "  logs      - Show logs from the telegram bot container"
    Write-Host "  status    - Show status of the telegram bot container"
    Write-Host "  build     - Build the telegram bot Docker image"
    Write-Host "  shell     - Open a shell in the telegram bot container"
    Write-Host "  health    - Check bot health"
    Write-Host "  setup     - Setup bot configuration"
    Write-Host "  clean     - Clean up containers and images"
    Write-Host ""
    exit 1
}

# Run main function
Main
