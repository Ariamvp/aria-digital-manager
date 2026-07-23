import os
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")

APPROVALS_FILE = "pending_approvals.json"

# Setup logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def send_actual_email(to_address, subject, body):
    """Sends the actual email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"Email failed: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Hello! I am A.R.I.A.'s Telegram assistant. \n\nReply with `status` to see pending approvals.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.lower() == 'status':
        if not os.path.exists(APPROVALS_FILE):
            await update.message.reply_text("No pending approvals.")
            return
        
        with open(APPROVALS_FILE, 'r') as f:
            tasks = json.load(f)
        
        pending = [t for t in tasks if t.get('status') == 'pending']
        if not pending:
            await update.message.reply_text("✅ All caught up! No pending approvals.")
        else:
            msg = "📋 *Pending Approvals:*\n\n"
            for t in pending:
                msg += f"ID: `{t['id']}`\nTo: {t['to']}\nSubject: {t['subject']}\n\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
            
    elif text.lower().startswith('send '):
        task_id = text.split(' ')[1].strip()
        
        if not os.path.exists(APPROVALS_FILE):
            await update.message.reply_text("No approvals file found.")
            return
            
        with open(APPROVALS_FILE, 'r') as f:
            tasks = json.load(f)
            
        task_found = False
        for t in tasks:
            if t['id'] == task_id and t['status'] == 'pending':
                task_found = True
                await update.message.reply_text(f"⏳ Processing ID {task_id}... Sending email to {t['to']}")
                
                success = send_actual_email(t['to'], t['subject'], t['body'])
                
                if success:
                    t['status'] = 'sent'
                    await update.message.reply_text(f"✅ Successfully sent email for ID {task_id}!")
                else:
                    t['status'] = 'failed'
                    await update.message.reply_text(f"❌ Failed to send email for ID {task_id}. Check logs.")
                break
                
        if not task_found:
            await update.message.reply_text(f"⚠️ Could not find pending task with ID: {task_id}")
            
        # Save updated status back to file
        with open(APPROVALS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2)
            
    else:
        await update.message.reply_text("Unknown command. Use `status` to view pending tasks, or `send <id>` to approve.")

def main():
    logger.info("Starting Telegram Bot...")
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()