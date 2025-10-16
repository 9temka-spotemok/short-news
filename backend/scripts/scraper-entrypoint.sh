#!/bin/bash
set -e

echo "🚀 Starting News Scraper Container..."
echo "📅 Scheduled to run every hour"

# Function to wait for database
wait_for_database() {
    echo "⏳ Waiting for database to be ready..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if python scripts/check_database.py 2>/dev/null; then
            echo "✅ Database is ready!"
            return 0
        fi
        
        echo "Attempt $attempt/$max_attempts: Database not ready, waiting 10 seconds..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    echo "❌ Database connection failed after $max_attempts attempts"
    exit 1
}

# Function to run scraper
run_scraper() {
    echo "🔍 Running news scraper..."
    cd /app
    
    # Run the scraper and capture output
    if python scripts/scrape_all_companies.py 2>&1 | tee -a /var/log/scraper.log; then
        echo "✅ Scraping completed successfully"
        echo "$(date): Scraping completed successfully" >> /var/log/scraper.log
    else
        echo "❌ Scraping failed"
        echo "$(date): Scraping failed" >> /var/log/scraper.log
    fi
}

# Function to run populate script
run_populate() {
    echo "📰 Running news population..."
    cd /app
    
    if python scripts/populate_news.py 2>&1 | tee -a /var/log/scraper.log; then
        echo "✅ News population completed successfully"
        echo "$(date): News population completed successfully" >> /var/log/scraper.log
    else
        echo "❌ News population failed"
        echo "$(date): News population failed" >> /var/log/scraper.log
    fi
}

# Main execution
main() {
    # Wait for database
    wait_for_database
    
    # Run initial scraping
    echo "🎯 Running initial scraping..."
    run_scraper
    run_populate
    
    # Start cron daemon
    echo "⏰ Starting cron daemon for scheduled scraping..."
    service cron start
    
    # Keep container running and show logs
    echo "📊 Container is running. Cron jobs will execute every hour."
    echo "📋 Recent logs:"
    tail -f /var/log/scraper.log
}

# Handle signals
trap 'echo "🛑 Received shutdown signal, stopping cron..."; service cron stop; exit 0' SIGTERM SIGINT

# Run main function
main

