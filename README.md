# DNS Monitor Bot

Monitors DNS records and alerts via Telegram if any changes are detected.

## Setup

1. Create `.env` file:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token
   CHAT_ID=your_chat_id
   DOMAIN=domain_to_monitor
   CHECK_INTERVAL=30
   ```

2. Get your Telegram Chat ID:
   - Message [@userinfobot](https://t.me/userinfobot)
   - Add the ID to your `.env` file

3. Run with Docker:
   ```sh
   docker build -t dns-monitor-bot .
   docker run --env-file .env dns-monitor-bot
   ```

## Configuration
- `TELEGRAM_TOKEN`: Bot token (required)
- `CHAT_ID`: Chat ID for notifications (required)
- `DOMAIN`: Domain to monitor (default: yearn.fi)
- `CHECK_INTERVAL`: Check frequency in seconds (default: 30) 