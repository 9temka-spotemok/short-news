# AI Competitor Insight Hub - Features Guide

This guide covers all the new features implemented in the platform.

## Table of Contents

1. [Personalized Digests](#personalized-digests)
2. [Telegram Integration](#telegram-integration)
3. [Micro-Notifications](#micro-notifications)
4. [Competitor Analysis](#competitor-analysis)
5. [API Reference](#api-reference)

---

## Personalized Digests

### Overview

Receive curated news digests based on your preferences, delivered on your schedule via web or Telegram.

### Features

**Frequency Options:**
- **Daily** - Receive digest every day
- **Weekly** - Once per week summary
- **Custom** - Set specific days and times

**Format Options:**
- **Short** - Headlines and links only
- **Detailed** - Full summaries and content

**Content Filters:**
- Filter by companies you follow
- Filter by news categories
- Filter by custom keywords

### How to Configure

1. Navigate to **Settings → Digest Settings**
2. Enable digests
3. Choose frequency (daily/weekly/custom)
4. Select format (short/detailed)
5. Configure content filters:
   - Add companies to follow
   - Select interested categories
   - Add keywords to track
6. (Optional) Enable Telegram delivery
7. Save settings

### Custom Schedule

For custom schedules, you can:
- Set specific time (e.g., 9:00 AM)
- Choose days of week (e.g., Monday-Friday)
- Set timezone (default: UTC)

Example: Receive digest every weekday at 9 AM

---

## Telegram Integration

### Overview

Receive personalized digests directly in Telegram through a private bot or subscribe to a public channel for general updates.

### Setup Steps

#### 1. Create Bot Connection

1. Find `@ai_insight_hub_bot` in Telegram
2. Send `/start` command
3. Bot will reply with your **Chat ID**
4. Copy the Chat ID (example: `123456789`)

#### 2. Configure in Web App

1. Go to **Settings → Digest Settings**
2. Scroll to **Telegram Integration**
3. Paste your Chat ID
4. Enable "Send to Telegram"
5. Save settings

#### 3. Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Get your Chat ID |
| `/help` | Show available commands |
| `/subscribe` | Subscribe to digests |
| `/unsubscribe` | Unsubscribe from digests |
| `/settings` | View current settings |
| `/digest` | Get latest digest now |

### Public Channel

Subscribe to `@ai_industry_news` for general AI industry updates.

### Troubleshooting

**Bot doesn't respond:**
- Check if you copied the correct Chat ID
- Ensure Telegram integration is enabled in settings
- Verify digest is enabled

**Not receiving digests:**
- Check your digest frequency settings
- Verify Chat ID is correct
- Ensure content filters aren't too restrictive

---

## Micro-Notifications

### Overview

Get real-time notifications about important events, similar to Dota 2's event system - small but informative updates that help you stay informed.

### Notification Types

#### 1. New News
- Triggered when companies you follow publish news
- Priority: Medium/High (depends on category)

#### 2. Company Active
- When a company publishes 3+ news items in 24 hours
- Priority: Medium
- Example: "OpenAI published 5 news items in the last 24 hours"

#### 3. Pricing Change
- When a followed company announces pricing changes
- Priority: High
- Example: "Anthropic: pricing_change - Claude Pro price update"

#### 4. Funding Announcement
- When a company announces funding
- Priority: High
- Example: "Perplexity AI raises $250M Series B"

#### 5. Product Launch
- When a company launches a new product
- Priority: High
- Example: "Google launches Gemini 2.0"

#### 6. Category Trend
- When a category has 5+ news items
- Priority: Low
- Example: "Trending: Model Release - 8 news items in the last 24 hours"

#### 7. Keyword Match
- When news matches your keywords
- Priority: High
- Example: "GPT-5 mentioned in new article"

#### 8. Competitor Milestone
- Important events from competitors
- Priority: Medium/High

### Notification Center

Access the notification center from the bell icon in the header:
- Shows unread count badge
- Quick preview of latest notifications
- Mark as read/delete actions
- Link to full notifications page

### Managing Notifications

**View All Notifications:**
- Navigate to **Notifications** page
- Filter by All/Unread
- Mark individual notifications as read
- Delete notifications

**Configure Settings:**
1. Go to notification settings
2. Enable/disable notification types
3. Set minimum priority threshold
4. Configure:
   - Company alerts (ON/OFF)
   - Category trends (ON/OFF)
   - Keyword alerts (ON/OFF)

### Best Practices

- Enable only relevant notification types
- Set higher priority threshold to reduce noise
- Regularly review and mark notifications as read
- Use keyword alerts for specific tracking

---

## Competitor Analysis

### Overview

Compare multiple companies side-by-side to understand competitive landscape.

### How to Use

1. Navigate to **Competitor Analysis** page
2. Select 2-5 companies to compare
3. Choose date range (default: last 30 days)
4. Click "Compare Companies"

### Comparison Metrics

#### 1. News Volume
- Total number of news articles per company
- Visual bar chart comparison
- Shows which competitors are most active

#### 2. Activity Score (0-100)
Based on:
- **News volume** (40 points) - How many articles published
- **Category diversity** (30 points) - Variety of news types
- **Recency** (30 points) - How recent the news is

Higher score = More active and diverse company activity

#### 3. Category Distribution
- Breakdown of news by category for each company
- Percentage distribution
- Top 5 categories shown

#### 4. Comparison Table
- Side-by-side comparison of all metrics
- Easy to spot leaders and laggards

### Use Cases

**Product Manager:**
- Track competitor product launches
- Monitor pricing changes
- Identify feature gaps

**Investor:**
- Assess company activity levels
- Compare portfolio companies
- Identify investment opportunities

**Marketing:**
- Monitor competitor announcements
- Track market positioning
- Identify partnership opportunities

### Saving Comparisons

Comparisons are automatically saved and can be accessed later:
- Navigate to saved comparisons
- View historical analysis
- Export data (coming soon)

---

## API Reference

### Digest Endpoints

#### Get Daily Digest
```bash
GET /api/v1/digest/daily
Authorization: Bearer {token}
```

#### Get Weekly Digest
```bash
GET /api/v1/digest/weekly
Authorization: Bearer {token}
```

#### Get Custom Digest
```bash
GET /api/v1/digest/custom?start_date=2025-01-01&end_date=2025-01-31
Authorization: Bearer {token}
```

#### Trigger Digest Generation (Async)
```bash
POST /api/v1/digest/generate?digest_type=daily
Authorization: Bearer {token}
```

### Digest Settings Endpoints

#### Get Digest Settings
```bash
GET /api/v1/users/preferences/digest
Authorization: Bearer {token}
```

#### Update Digest Settings
```bash
PUT /api/v1/users/preferences/digest
Content-Type: application/json
Authorization: Bearer {token}

{
  "digest_enabled": true,
  "digest_frequency": "daily",
  "digest_format": "short",
  "digest_include_summaries": true,
  "telegram_chat_id": "123456789",
  "telegram_enabled": true
}
```

### Notification Endpoints

#### Get Notifications
```bash
GET /api/v1/notifications/?skip=0&limit=20&unread_only=false
Authorization: Bearer {token}
```

#### Get Unread Notifications
```bash
GET /api/v1/notifications/unread
Authorization: Bearer {token}
```

#### Mark Notification as Read
```bash
PUT /api/v1/notifications/{notification_id}/read
Authorization: Bearer {token}
```

#### Mark All as Read
```bash
PUT /api/v1/notifications/mark-all-read
Authorization: Bearer {token}
```

#### Get Notification Settings
```bash
GET /api/v1/notifications/settings
Authorization: Bearer {token}
```

#### Update Notification Settings
```bash
PUT /api/v1/notifications/settings
Content-Type: application/json
Authorization: Bearer {token}

{
  "enabled": true,
  "company_alerts": true,
  "category_trends": true,
  "keyword_alerts": true,
  "min_priority_score": 0
}
```

### Competitor Analysis Endpoints

#### Compare Companies
```bash
POST /api/v1/competitors/compare
Content-Type: application/json
Authorization: Bearer {token}

{
  "company_ids": ["uuid1", "uuid2", "uuid3"],
  "date_from": "2025-01-01",
  "date_to": "2025-01-31",
  "name": "Q1 2025 Comparison"
}
```

#### Get Saved Comparisons
```bash
GET /api/v1/competitors/comparisons?limit=10
Authorization: Bearer {token}
```

#### Get Specific Comparison
```bash
GET /api/v1/competitors/comparisons/{comparison_id}
Authorization: Bearer {token}
```

#### Get Company Activity
```bash
GET /api/v1/competitors/activity/{company_id}?days=30
Authorization: Bearer {token}
```

---

## Tips & Tricks

### Digest Optimization

1. **Start with daily digest** to understand your preferences
2. **Refine keywords** based on what you find useful
3. **Adjust format** - try both short and detailed
4. **Use custom schedule** for optimal timing

### Notification Management

1. **Start with all types enabled**, then refine
2. **Review weekly** and adjust settings
3. **Use keyword alerts** for critical tracking
4. **Set minimum priority** to reduce noise

### Competitor Analysis

1. **Compare similar companies** for meaningful insights
2. **Use 30-day range** for trend analysis
3. **Track consistently** - weekly or monthly
4. **Save important comparisons** for reference

### Telegram Best Practices

1. **Get Chat ID first** before configuring
2. **Test with /digest** command
3. **Subscribe to channel** for general updates
4. **Use bot commands** for quick access

---

## Support

If you need help:
- Check [TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md) for Telegram setup
- Review API documentation above
- Contact: team@shot-news.com

---

**Last Updated:** October 14, 2025
**Version:** 1.0.0

