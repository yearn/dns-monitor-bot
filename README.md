# DNS Monitor Bot

This bot monitors the DNS of `yearn.fi` every 30 seconds and alerts you via Telegram if the IP changes.

## Setup

1. **Get your Telegram Chat ID:**
   - Start a chat with [@userinfobot](https://t.me/userinfobot) on Telegram.
   - Send any message and it will reply with your chat ID.
   - Replace `YOUR_CHAT_ID_HERE` in `bot.py` with your chat ID.

2. **Build and Run Locally:**
   ```sh
   pip install -r requirements.txt
   python bot.py
   ```

3. **Deploy to Fly.io:**
   - Install [Fly CLI](https://fly.io/docs/hands-on/install-flyctl/)
   - Run:
     ```sh
     fly launch --now
     ```
   - Follow prompts to deploy your bot.

## Configuration
- Edit `CHECK_INTERVAL` in `bot.py` to change the check frequency (default: 30 seconds).
- The bot token is already set in `bot.py`.

## Security
- This bot helps detect DNS hijacking or attacks on your domain. 