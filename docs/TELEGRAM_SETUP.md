# Telegram Integration Setup Guide

This guide explains how to set up Telegram integration for AI Competitor Insight Hub to receive personalized news digests.

## Overview

The platform supports two types of Telegram integration:

1. **Personal Bot** - Users receive personalized digests in private messages
2. **Public Channel** - General digests posted to a public channel for all subscribers

## Creating a Telegram Bot

### Step 1: Create Bot with BotFather

1. Open Telegram and search for `@BotFather`
2. Start a chat and send `/newbot` command
3. Follow the prompts:
   - Choose a name for your bot (e.g., "AI Insight Hub")
   - Choose a username ending in "bot" (e.g., "ai_insight_hub_bot")
4. BotFather will provide you with a **Bot Token** - save this securely!

Example token format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567`

### Step 2: Configure Bot Settings

1. Send `/setdescription` to BotFather
   - Description: "Get personalized AI industry news digests"

2. Send `/setabouttext` to BotFather
   - About: "AI Competitor Insight Hub - Your personalized AI news digest bot"

3. Send `/setcommands` to BotFather
   - Paste this command list:
```
start - Start the bot and get your Chat ID
help - Show available commands
subscribe - Subscribe to digests
unsubscribe - Unsubscribe from digests
settings - View current settings
digest - Get latest digest now
```

### Step 3: Add Bot Token to Environment

Add the bot token to your `.env` file:

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-1234567
```

## Creating a Public Channel (Optional)

If you want to post general digests to a public channel:

### Step 1: Create Channel

1. Open Telegram
2. Menu → New Channel
3. Choose a name (e.g., "AI Industry News")
4. Choose Public or Private
5. Add a username (e.g., "@ai_industry_news")

### Step 2: Add Bot as Administrator

1. Open your channel
2. Settings → Administrators
3. Add Administrator
4. Search for your bot username
5. Grant "Post Messages" permission

### Step 3: Get Channel ID

For public channels, the ID is the username with @ symbol:
```env
TELEGRAM_CHANNEL_ID=@ai_industry_news
```

For private channels, you'll need to get the numeric ID:
1. Add the bot to your channel
2. Send a test message
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find the "chat" object and copy the "id" field

```env
TELEGRAM_CHANNEL_ID=-1001234567890
```

## User Setup

### Step 1: Get Chat ID

Users need to get their Chat ID to receive personalized digests:

1. Open Telegram
2. Search for your bot (e.g., `@ai_insight_hub_bot`)
3. Send `/start` command
4. Bot will reply with your Chat ID (e.g., `123456789`)
5. Copy this Chat ID

### Step 2: Add Chat ID to Profile

1. Log in to AI Competitor Insight Hub web app
2. Go to Settings → Digest Settings
3. Paste your Chat ID in the "Telegram Chat ID" field
4. Enable "Send digests to Telegram"
5. Configure digest frequency and format
6. Save settings

## Digest Configuration

### Frequency Options

- **Daily** - Receive digest every day at specified time
- **Weekly** - Receive digest once per week
- **Custom** - Set custom schedule (specific days and times)

### Format Options

- **Short** - Brief headlines and links only
- **Detailed** - Full summaries and content

### Content Filters

Configure what news you want to receive:
- **Companies** - Select specific companies to follow
- **Categories** - Choose news categories (funding, product updates, etc.)
- **Keywords** - Add custom keywords to track

## Testing

### Test Personal Digest

1. Open your bot in Telegram
2. Send `/digest` command
3. You should receive a digest based on your preferences

### Test Channel Digest

Wait for the scheduled channel digest (daily at midnight UTC) or trigger manually via API:

```bash
curl -X POST http://localhost:8000/api/v1/admin/trigger-channel-digest \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Bot doesn't respond

- Check that `TELEGRAM_BOT_TOKEN` is correct in `.env`
- Verify bot is running (Celery worker should be active)
- Check logs for errors

### Digest not received

- Verify Chat ID is correct (send `/start` to bot to get it)
- Check that "Telegram enabled" is ON in settings
- Verify digest is enabled and configured
- Check Celery beat scheduler is running

### Channel posting fails

- Verify bot is administrator in channel
- Check that bot has "Post Messages" permission
- Verify `TELEGRAM_CHANNEL_ID` is correct

### Invalid Chat ID error

- Chat ID should be numeric (e.g., `123456789`)
- Don't include @ symbol
- Make sure you copied the entire number

## Bot Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `/start` | Get your Chat ID and start using the bot | `/start` |
| `/help` | Show all available commands | `/help` |
| `/subscribe` | Subscribe to digests | `/subscribe` |
| `/unsubscribe` | Unsubscribe from digests | `/unsubscribe` |
| `/settings` | View current settings | `/settings` |
| `/digest` | Get latest digest immediately | `/digest` |

## Security Notes

1. **Never share your Bot Token** - It's like a password for your bot
2. **Keep Chat IDs private** - They can be used to send messages to users
3. **Use HTTPS** - Always use secure connections for webhooks (production)
4. **Validate inputs** - Bot should validate all user inputs

## Advanced Configuration

### Custom Schedules

Users can configure custom digest schedules:

```json
{
  "time": "09:00",
  "days": [1, 2, 3, 4, 5],  // Monday-Friday
  "timezone": "UTC"
}
```

### Notification Types

Configure which types of notifications to receive:

- New news from followed companies
- Pricing changes
- Funding announcements
- Category trends
- Keyword matches

## API Integration

For developers who want to integrate programmatically:

### Get User's Telegram Settings

```bash
GET /api/v1/users/preferences/digest
Authorization: Bearer YOUR_TOKEN
```

### Update Telegram Settings

```bash
PUT /api/v1/users/preferences/digest
Content-Type: application/json
Authorization: Bearer YOUR_TOKEN

{
  "telegram_chat_id": "123456789",
  "telegram_enabled": true,
  "digest_enabled": true,
  "digest_frequency": "daily",
  "digest_format": "short"
}
```

### Trigger Manual Digest

```bash
POST /api/v1/digest/generate?digest_type=daily
Authorization: Bearer YOUR_TOKEN
```

## Support

If you encounter issues:

1. Check the logs: `docker-compose logs backend`
2. Verify environment variables: `docker-compose exec backend env | grep TELEGRAM`
3. Test bot token: Visit `https://api.telegram.org/bot<TOKEN>/getMe`
4. Contact support: team@shot-news.com

## Resources

- [Telegram Bot API Documentation](https://core.telegram.org/bots/api)
- [BotFather Guide](https://core.telegram.org/bots#6-botfather)
- [Telegram Channels](https://telegram.org/tour/channels)



