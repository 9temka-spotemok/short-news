#!/bin/bash

# Telegram Bot Docker Management Script
# This script helps manage the Telegram bot Docker container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Telegram Bot Docker Management Script"
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     - Start the telegram bot container"
    echo "  stop      - Stop the telegram bot container"
    echo "  restart   - Restart the telegram bot container"
    echo "  logs      - Show logs from the telegram bot container"
    echo "  status    - Show status of the telegram bot container"
    echo "  build     - Build the telegram bot Docker image"
    echo "  shell     - Open a shell in the telegram bot container"
    echo "  health    - Check bot health"
    echo "  setup     - Setup bot configuration"
    echo "  clean     - Clean up containers and images"
    echo ""
}

# Function to check if docker-compose is available
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null && ! command -v docker &> /dev/null; then
        print_error "Docker and docker-compose are not installed!"
        exit 1
    fi
    
    # Use docker compose (newer) or docker-compose (older)
    if command -v docker &> /dev/null && docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
        COMPOSE_CMD="docker-compose"
    else
        print_error "Neither 'docker compose' nor 'docker-compose' is available!"
        exit 1
    fi
}

# Function to start the bot
start_bot() {
    print_status "Starting Telegram bot container..."
    
    # Go to project root directory
    cd "$(dirname "$0")/../.."
    
    $COMPOSE_CMD up -d telegram-bot
    
    if [ $? -eq 0 ]; then
        print_success "Telegram bot container started successfully!"
        print_status "Use '$0 logs' to view logs"
        print_status "Use '$0 status' to check status"
    else
        print_error "Failed to start telegram bot container!"
        exit 1
    fi
}

# Function to stop the bot
stop_bot() {
    print_status "Stopping Telegram bot container..."
    
    cd "$(dirname "$0")/../.."
    
    $COMPOSE_CMD stop telegram-bot
    
    if [ $? -eq 0 ]; then
        print_success "Telegram bot container stopped successfully!"
    else
        print_error "Failed to stop telegram bot container!"
        exit 1
    fi
}

# Function to restart the bot
restart_bot() {
    print_status "Restarting Telegram bot container..."
    
    cd "$(dirname "$0")/../.."
    
    $COMPOSE_CMD restart telegram-bot
    
    if [ $? -eq 0 ]; then
        print_success "Telegram bot container restarted successfully!"
    else
        print_error "Failed to restart telegram bot container!"
        exit 1
    fi
}

# Function to show logs
show_logs() {
    print_status "Showing Telegram bot logs (Ctrl+C to exit)..."
    
    cd "$(dirname "$0")/../.."
    
    $COMPOSE_CMD logs -f telegram-bot
}

# Function to show status
show_status() {
    print_status "Telegram bot container status:"
    
    cd "$(dirname "$0")/../.."
    
    $COMPOSE_CMD ps telegram-bot
    
    echo ""
    print_status "Container health:"
    docker inspect shot-news-telegram-bot --format='{{.State.Health.Status}}' 2>/dev/null || echo "No health check available"
}

# Function to build the bot image
build_bot() {
    print_status "Building Telegram bot Docker image..."
    
    cd "$(dirname "$0")/../.."
    
    $COMPOSE_CMD build telegram-bot
    
    if [ $? -eq 0 ]; then
        print_success "Telegram bot image built successfully!"
    else
        print_error "Failed to build telegram bot image!"
        exit 1
    fi
}

# Function to open shell in container
open_shell() {
    print_status "Opening shell in Telegram bot container..."
    
    docker exec -it shot-news-telegram-bot /bin/bash
    
    if [ $? -eq 0 ]; then
        print_success "Shell session ended"
    else
        print_error "Failed to open shell in container!"
        exit 1
    fi
}

# Function to check bot health
check_health() {
    print_status "Checking Telegram bot health..."
    
    # Check if container is running
    if ! docker ps | grep -q shot-news-telegram-bot; then
        print_error "Telegram bot container is not running!"
        exit 1
    fi
    
    # Check container health
    health_status=$(docker inspect shot-news-telegram-bot --format='{{.State.Health.Status}}' 2>/dev/null)
    
    if [ "$health_status" = "healthy" ]; then
        print_success "Telegram bot is healthy!"
    elif [ "$health_status" = "unhealthy" ]; then
        print_error "Telegram bot is unhealthy!"
        print_status "Check logs with: $0 logs"
        exit 1
    else
        print_warning "Health check status: $health_status"
    fi
    
    # Test bot API
    print_status "Testing bot API connection..."
    
    # Get bot token from environment
    bot_token=$(docker exec shot-news-telegram-bot printenv TELEGRAM_BOT_TOKEN 2>/dev/null)
    
    if [ -z "$bot_token" ]; then
        print_error "TELEGRAM_BOT_TOKEN not found in container!"
        exit 1
    fi
    
    # Test API call
    response=$(curl -s "https://api.telegram.org/bot$bot_token/getMe")
    
    if echo "$response" | grep -q '"ok":true'; then
        print_success "Bot API connection successful!"
        bot_name=$(echo "$response" | grep -o '"first_name":"[^"]*"' | cut -d'"' -f4)
        bot_username=$(echo "$response" | grep -o '"username":"[^"]*"' | cut -d'"' -f4)
        echo "  Bot name: $bot_name"
        echo "  Bot username: @$bot_username"
    else
        print_error "Bot API connection failed!"
        echo "Response: $response"
        exit 1
    fi
}

# Function to setup bot configuration
setup_bot() {
    print_status "Setting up Telegram bot configuration..."
    
    cd "$(dirname "$0")/../.."
    
    # Check if .env file exists
    if [ ! -f "backend/.env" ]; then
        print_warning ".env file not found, creating from example..."
        if [ -f "backend/env.example" ]; then
            cp backend/env.example backend/.env
            print_status "Please edit backend/.env file with your configuration"
        else
            print_error "env.example file not found!"
            exit 1
        fi
    fi
    
    # Run the interactive setup script
    print_status "Running interactive bot setup..."
    cd backend
    python setup_telegram_bot_interactive.py
    
    if [ $? -eq 0 ]; then
        print_success "Bot setup completed!"
        print_status "You can now start the bot with: $0 start"
    else
        print_error "Bot setup failed!"
        exit 1
    fi
}

# Function to clean up
clean_up() {
    print_status "Cleaning up Telegram bot containers and images..."
    
    cd "$(dirname "$0")/../.."
    
    # Stop and remove container
    $COMPOSE_CMD stop telegram-bot 2>/dev/null || true
    $COMPOSE_CMD rm -f telegram-bot 2>/dev/null || true
    
    # Remove image
    docker rmi $(docker images | grep 'shot-news.*telegram-bot' | awk '{print $3}') 2>/dev/null || true
    
    print_success "Cleanup completed!"
}

# Main script logic
main() {
    check_docker_compose
    
    case "${1:-}" in
        start)
            start_bot
            ;;
        stop)
            stop_bot
            ;;
        restart)
            restart_bot
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        build)
            build_bot
            ;;
        shell)
            open_shell
            ;;
        health)
            check_health
            ;;
        setup)
            setup_bot
            ;;
        clean)
            clean_up
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

