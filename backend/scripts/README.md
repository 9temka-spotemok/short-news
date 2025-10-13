# News Scraping Scripts

## Overview

This directory contains scripts for importing competitor companies from CSV and scraping news from their websites.

## Available Scripts

### 1. Import Competitors from CSV
`import_competitors_from_csv.py` - Parses CSV file and imports companies to database

### 2. Scrape All Companies
`scrape_all_companies.py` - Scrapes news from all companies in database

### 3. Full Import (Docker)
`import_from_docker.py` - Complete import and scraping process for Docker environment

### 4. Run Full Import
`run_full_import.py` - Complete import and scraping process for local environment

## Usage

### Running in Docker (Recommended)

1. Copy CSV file to Docker container:
```bash
docker cp "../.playwright-mcp/Копия-SKOUR-Competitor-Matrix---✦-Skour-Competitors.csv" shot-news-backend:/app/competitors.csv
```

2. Run the import script:
```bash
docker exec -it shot-news-backend python scripts/import_from_docker.py
```

### Running Locally

1. Ensure PostgreSQL and Redis are running:
```bash
docker-compose up -d postgres redis
```

2. Set up environment:
```bash
cp env.example .env
# Edit .env with correct DATABASE_URL
```

3. Run the script:
```bash
python scripts/run_full_import.py
```

## Components Created

### 1. UniversalBlogScraper (`app/scrapers/universal_scraper.py`)
- Automatically detects blog/news URLs from company websites
- Supports multiple common blog patterns (/blog, /news, /insights, etc.)
- Extracts articles using various HTML selectors
- Returns max 5 articles per company by default

### 2. Import Scripts
- **CSV Parser**: Extracts company data from CSV file
- **Database Import**: Adds companies to PostgreSQL database  
- **News Scraper**: Scrapes news from all companies
- **News Storage**: Saves scraped news items to database

## Features

- ✅ Parses 120+ competitor companies from CSV
- ✅ Automatically detects blog/news pages
- ✅ Scrapes up to 5 articles per company
- ✅ Stores company info and news in database
- ✅ Handles duplicates gracefully
- ✅ Detailed logging and progress tracking

## Database Schema

Companies are stored with:
- `name` - Company name
- `website` - Company website URL
- `description` - Company description with pricing/features
- `category` - "geo_competitor" for imported competitors
- `twitter_handle` - Twitter/X handle (if available)

News items are stored with:
- `title` - Article title
- `content` - Article content
- `summary` - Article summary
- `source_url` - Original article URL
- `source_type` - Type of source (blog, news_site, etc.)
- `company_id` - Reference to company
- `published_at` - Publication date

## Troubleshooting

### Database Connection Issues
- Ensure Docker containers are running: `docker-compose ps`
- Check DATABASE_URL in .env file
- Verify PostgreSQL is accessible on port 5432

### CSV File Not Found
- Ensure CSV file path is correct
- For Docker: Copy file to container first
- Check file permissions

### Duplicate Companies
- Script skips existing companies automatically
- Check logs for skipped companies
- Some duplicates in CSV are expected (e.g. "Gauge" appears twice)

## Notes

- The universal scraper works best with standard blog/news structures
- Some websites may block scraping or have non-standard layouts
- Scraping rate is limited to avoid overwhelming target servers
- Results may vary based on website structure and availability




