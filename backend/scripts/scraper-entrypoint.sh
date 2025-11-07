#!/bin/bash
set -euo pipefail

log_info() {
    printf '[scraper][%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1"
}

log_error() {
    printf '[scraper][%s][ERROR] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$1" >&2
}

wait_for_database() {
    log_info "Waiting for database to be ready"
    local max_attempts=30
    local attempt=1

    while [ "$attempt" -le "$max_attempts" ]; do
        if python scripts/check_database.py >/dev/null 2>&1; then
            log_info "Database is ready"
            return 0
        fi

        log_info "Attempt ${attempt}/${max_attempts}: database not ready, retrying in 10s"
        sleep 10
        attempt=$((attempt + 1))
    done

    log_error "Database connection failed after ${max_attempts} attempts"
    return 1
}

run_scraper() {
    log_info "Running scrape_all_companies"
    if python scripts/scrape_all_companies.py 2>&1 | tee -a /var/log/scraper.log; then
        log_info "Scraping completed successfully"
        printf '%s Scraping completed successfully\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> /var/log/scraper.log
    else
        log_error "Scraping failed"
        printf '%s Scraping failed\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> /var/log/scraper.log
    fi
}

run_populate() {
    log_info "Running populate_news"
    if python scripts/populate_news.py 2>&1 | tee -a /var/log/scraper.log; then
        log_info "News population completed successfully"
        printf '%s News population completed successfully\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> /var/log/scraper.log
    else
        log_error "News population failed"
        printf '%s News population failed\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" >> /var/log/scraper.log
    fi
}

start_cron() {
    log_info "Starting cron daemon"
    service cron start
}

follow_logs() {
    log_info "Container is running. Tail logs from /var/log/scraper.log"
    touch /var/log/scraper.log
    tail -F /var/log/scraper.log
}

shutdown() {
    log_info "Stopping cron daemon"
    service cron stop || true
    exit 0
}

trap shutdown SIGTERM SIGINT

main() {
    cd /app
    wait_for_database
    run_scraper
    run_populate
    start_cron
    follow_logs
}

main "$@"
