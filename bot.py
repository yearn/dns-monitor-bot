import asyncio
import socket
import dns.resolver
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError

TELEGRAM_TOKEN = "7622164449:AAHSoqDGItig9OsgMiQP6qx8l2Eek1_A25w"
CHAT_ID = "-1002426136698"  # Replace with your chat ID
DOMAIN = "yearn.fi"
CHECK_INTERVAL = 30  # seconds

async def resolve_domain(domain):
    try:
        return socket.gethostbyname(domain)
    except Exception as e:
        return f"ERROR: {e}"

def get_dns_details(domain):
    details = {}
    resolver = dns.resolver.Resolver()
    try:
        a_records = [r.address for r in resolver.resolve(domain, 'A')]
        details['A'] = a_records
    except Exception as e:
        pass
    try:
        aaaa_records = [r.address for r in resolver.resolve(domain, 'AAAA')]
        details['AAAA'] = aaaa_records
    except Exception as e:
        pass
    try:
        cname_records = [r.target.to_text() for r in resolver.resolve(domain, 'CNAME')]
        details['CNAME'] = cname_records
    except Exception as e:
        pass
    try:
        mx_records = [f"{r.preference} {r.exchange}" for r in resolver.resolve(domain, 'MX')]
        details['MX'] = mx_records
    except Exception as e:
        pass
    try:
        ns_records = [r.target.to_text() for r in resolver.resolve(domain, 'NS')]
        details['NS'] = ns_records
    except Exception as e:
        pass
    try:
        txt_records = [b''.join(r.strings).decode('utf-8', errors='replace') for r in resolver.resolve(domain, 'TXT')]
        details['TXT'] = txt_records
    except Exception as e:
        pass
    return details

def format_dns_details(details):
    formatted = []
    for record_type, records in details.items():
        if records:
            formatted.append(f"{record_type}: {', '.join(records)}")
    return '\n'.join(formatted)

async def notify_change(bot, old_details, new_details):
    changes = []
    for record_type in set(old_details.keys()) | set(new_details.keys()):
        old_records = old_details.get(record_type, [])
        new_records = new_details.get(record_type, [])
        if old_records != new_records:
            changes.append(f"{record_type}:\nOld: {', '.join(old_records) if old_records else 'None'}\nNew: {', '.join(new_records) if new_records else 'None'}")
    
    if changes:
        msg = f"[ALERT] DNS changes detected for {DOMAIN}!\n\n" + "\n\n".join(changes)
        try:
            await bot.send_message(chat_id=CHAT_ID, text=msg)
        except TelegramError as e:
            print(f"Failed to send Telegram message: {e}")

async def monitor_dns(bot):
    last_details = get_dns_details(DOMAIN)
    print(f"Initial DNS for {DOMAIN}:")
    print(format_dns_details(last_details))
    
    while True:
        await asyncio.sleep(CHECK_INTERVAL)
        current_details = get_dns_details(DOMAIN)
        if current_details != last_details:
            print(f"DNS changes detected for {DOMAIN}")
            await notify_change(bot, last_details, current_details)
            last_details = current_details
        else:
            print(f"No changes detected for {DOMAIN}")

async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    details = get_dns_details(DOMAIN)
    msg = f"Current DNS for {DOMAIN}:\n{format_dns_details(details)}"
    # Telegram messages have a 4096 char limit
    if len(msg) > 4000:
        msg = msg[:4000] + "... (truncated)"
    await update.message.reply_text(msg)

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = f"🔍 DNS Monitor Status\n\nDomain: {DOMAIN}\nCheck Interval: {CHECK_INTERVAL} seconds\nChat ID: {CHAT_ID}"
    await update.message.reply_text(msg)

async def start_background_tasks(application):
    application.create_task(monitor_dns(application.bot))

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("status", status_command))
    application.post_init = start_background_tasks
    
    # Run the bot with proper asyncio handling
    asyncio.run(application.run_polling())

if __name__ == "__main__":
    main() 