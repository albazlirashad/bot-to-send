import telebot
import re
import time
import os
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# قاموس لتخزين معرف القناة لكل مستخدم بشكل مؤقت
user_channels = {}

def parse_questions_universal(text):
    blocks = re.split(r'\n\s*\n', text.strip())
    if len(blocks) <= 1:
        blocks = re.split(r'\n(?=\d+[\.\-\)])|^(?=\d+[\.\-\)])', text.strip())

    parsed_data = []
    for block in blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if len(lines) < 2: continue

        question_raw = lines[0]
        question_text = re.sub(r'^\d+[\s\.\-\)]+', '', question_raw)
        question_text = re.sub(r'\[\d+.*?\]', '', question_text).strip()

        options = []
        correct_index = -1

        for line in lines[1:]:
            is_correct = '<' in line and '>' in line
            clean_opt = line.replace('•', '').replace('<', '').replace('>', '')
            clean_opt = re.sub(r'\[\d+.*?\]', '', clean_opt).strip()

            if clean_opt:
                options.append(clean_opt)
                if is_correct:
                    correct_index = len(options) - 1

        if len(options) >= 2 and correct_index != -1:
            parsed_data.append({
                'question': question_text,
                'options': options,
                'correct': correct_index
            })
    return parsed_data

@bot.message_handler(commands=['start'])
def start_command(message):
    msg = bot.reply_to(message, "👋 أهلاً بك! أولاً، أرسل لي معرف القناة التي تريد النشر فيها (مثال: @mychannel):")
    bot.register_next_step_handler(msg, get_channel_id)

def get_channel_id(message):
    channel_id = message.text.strip()
    if not channel_id.startswith('@'):
        msg = bot.reply_to(message, "⚠️ خطأ! يجب أن يبدأ المعرف بـ @. حاول مرة أخرى:")
        bot.register_next_step_handler(msg, get_channel_id)
        return

    user_channels[message.chat.id] = channel_id
    
    welcome_text = (
        f"✅ تم ضبط القناة على: {channel_id}\n\n"
        "🚀 **الآن أرسل الأسئلة بالتنسيق المطلوب وسيتم نشرها فوراً!**\n\n"
        "💡 ملاحظة: يجب أن يكون البوت **آدمن (Admin)** في القناة."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_questions(message):
    # التحقق مما إذا كان المستخدم قد حدد القناة
    if message.chat.id not in user_channels:
        msg = bot.reply_to(message, "⚠️ من فضلك أرسل معرف القناة أولاً (@channel):")
        bot.register_next_step_handler(msg, get_channel_id)
        return

    channel_id = user_channels[message.chat.id]
    questions = parse_questions_universal(message.text)
    
    if not questions:
        bot.reply_to(message, "⚠️ لم يتم التعرف على الأسئلة. تأكد من التنسيق.")
        return

    bot.reply_to(message, f"⏳ جاري النشر في {channel_id}...")
    sent_count = 0
    for q in questions:
        try:
            bot.send_poll(
                chat_id=channel_id,
                question=q['question'],
                options=q['options'],
                type='quiz',
                correct_option_id=q['correct'],
                is_anonymous=True
            )
            sent_count += 1
            time.sleep(2)
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ خطأ في النشر: تأكد أن البوت مسؤول في القناة.")
            break

    bot.send_message(message.chat.id, f"✅ تم نشر {sent_count} سؤال بنجاح.")

if __name__ == "__main__":
    Thread(target=run_web_server).start()
    print("البوت يعمل...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(5)
