import asyncio
import socket
import dns.resolver
import logging
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get configuration from environment variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
DOMAIN = os.getenv('DOMAIN', 'yearn.fi')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', '30'))
last_ping_time = datetime.now()  # Track last ping time

# Validate required environment variables
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is required")
if not CHAT_ID:
    raise ValueError("CHAT_ID environment variable is required")

async def resolve_domain(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception as e:
        logger.error(f"Error resolving domain {domain}: {e}")
        return f"ERROR: {e}"

def get_dns_details(domain):
    details = {}
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5.0  # Set timeout to 5 seconds
    resolver.lifetime = 10.0  # Set total timeout to 10 seconds
    
    record_types = {
        'A': lambda r: [r.address for r in r],
        'AAAA': lambda r: [r.address for r in r],
        'CNAME': lambda r: [r.target.to_text() for r in r],
        'MX': lambda r: [f"{r.preference} {r.exchange}" for r in r],
        'NS': lambda r: [r.target.to_text() for r in r],
        'TXT': lambda r: [b''.join(r.strings).decode('utf-8', errors='replace') for r in r]
    }
    
    for record_type, formatter in record_types.items():
        try:
            records = resolver.resolve(domain, record_type)
            details[record_type] = formatter(records)
        # except dns.resolver.NXDOMAIN:
        #     logger.warning(f"No {record_type} records found for {domain}")
        # except dns.resolver.NoAnswer:
        #     logger.warning(f"No {record_type} records found for {domain}")
        except dns.resolver.Timeout:
            logger.error(f"Timeout resolving {record_type} records for {domain}")
        except Exception as e:
            logger.error(f"Error resolving {record_type} records for {domain}: {e}")
    
    return details

def format_dns_details(details):
    if not details:
        return "No DNS records found"
    
    formatted = []
    for record_type, records in details.items():
        if records:
            formatted.append(f"{record_type}: {' | '.join(sorted(records))}")
    return '\n'.join(formatted) if formatted else "No DNS records found"

async def notify_change(bot, old_details, new_details):
    changes = []
    for record_type in set(old_details.keys()) | set(new_details.keys()):
        old_records = sorted(old_details.get(record_type, []))
        new_records = sorted(new_details.get(record_type, []))
        if old_records != new_records:
            changes.append(f"{record_type}:\nOld: {' | '.join(old_records) if old_records else 'None'}\nNew: {' | '.join(new_records) if new_records else 'None'}")
    
    if changes:
        msg = f"[ALERT] DNS changes detected for {DOMAIN}!\n\n" + "\n\n".join(changes)
        try:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
            logger.info(f"Sent notification about DNS changes for {DOMAIN}")
        except TelegramError as e:
            logger.error(f"Failed to send Telegram message: {e}")

async def monitor_dns(bot):
    global last_ping_time
    logger.info(f"Starting DNS monitoring for {DOMAIN}")
    last_details = get_dns_details(DOMAIN)
    logger.info(f"Initial DNS for {DOMAIN}:\n{format_dns_details(last_details)}")
    
    while True:
        try:
            await asyncio.sleep(CHECK_INTERVAL)
            current_details = get_dns_details(DOMAIN)
            last_ping_time = datetime.now()  # Update last ping time
            if current_details != last_details:
                logger.info(f"DNS changes detected for {DOMAIN}")
                await notify_change(bot, last_details, current_details)
                last_details = current_details
            else:
                logger.info(f"Ping successful - No DNS changes detected for {DOMAIN}")
        except Exception as e:
            logger.error(f"Error in monitor_dns: {e}")
            await asyncio.sleep(CHECK_INTERVAL)  # Wait before retrying

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        details = get_dns_details(DOMAIN)
        msg = f"Current DNS for {DOMAIN}:\n{format_dns_details(details)}"
        # Telegram messages have a 4096 char limit
        if len(msg) > 4000:
            msg = msg[:4000] + "... (truncated)"
        await update.message.reply_text(msg)
        logger.info(f"Sent DNS check response to user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in check_command: {e}")
        await update.message.reply_text("Sorry, there was an error checking the DNS records.")

def format_time_ago(dt):
    now = datetime.now()
    diff = now - dt
    
    if diff < timedelta(minutes=1):
        return "🟢 just now"
    elif diff < timedelta(hours=1):
        minutes = int(diff.total_seconds() / 60)
        return f"🔴 {minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < timedelta(days=1):
        hours = int(diff.total_seconds() / 3600)
        return f"🔴 {hours} hour{'s' if hours != 1 else ''} ago"
    elif diff < timedelta(days=30):
        days = int(diff.total_seconds() / 86400)
        return f"🔴 {days} day{'s' if days != 1 else ''} ago"
    else:
        return dt.strftime('%Y-%m-%d %H:%M:%S')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        msg = f"🔍 DNS Monitor Status\n\nDomain: {DOMAIN}\nCheck Interval: {CHECK_INTERVAL} seconds\nChat ID: {CHAT_ID}\nLast Ping: {format_time_ago(last_ping_time)}"
        await update.message.reply_text(msg)
        logger.info(f"Sent status response to user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in status_command: {e}")
        await update.message.reply_text("Sorry, there was an error getting the status.")

async def start_background_tasks(application):
    application.create_task(monitor_dns(application.bot))
    logger.info("Background tasks started")

def main():
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("status", status_command))
    
    # Set up background tasks
    application.post_init = start_background_tasks
    
    # Start the bot
    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main() 
