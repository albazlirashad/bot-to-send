import telebot
from telebot import types
import re
import time
import os
import sqlite3
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

# --- إعداد خادم الويب لـ Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- إعدادات البوت وقاعدة البيانات ---
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, channel_id TEXT)''')
    conn.commit()
    conn.close()

# إعداد قائمة الأوامر والزر الجانبي (Menu Button)
def set_bot_commands():
    commands = [
        types.BotCommand("start", "🚀 بدء البوت / إعادة ضبط"),
        types.BotCommand("settings", "⚙️ إعدادات القناة"),
        types.BotCommand("help", "❓ تعليمات التنسيق")
    ]
    bot.set_my_commands(commands)

def set_user_channel(user_id, channel_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('REPLACE INTO users (user_id, channel_id) VALUES (?, ?)', (user_id, channel_id))
    conn.commit()
    conn.close()

def get_user_channel(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT channel_id FROM users WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# --- معالجة الأسئلة ---
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
            parsed_data.append({'question': question_text, 'options': options, 'correct': correct_index})
    return parsed_data

# --- الردود والأوامر ---

@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = (
        "👋 **أهلاً بك في بوت نشر الاختبارات التفاعلية**\n\n"
        "هذا البوت يساعدك على تنسيق ونشر الأسئلة في قناتك بشكل آلي وسريع.\n"
        "استخدم زر **Menu** الجانبي للوصول السريع للأوامر."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    time.sleep(1)
    
    msg = bot.send_message(message.chat.id, "📍 **الخطوة الأولى:** أرسل معرف القناة (مثال: @mychannel):")
    bot.register_next_step_handler(msg, save_channel_step)

def save_channel_step(message):
    channel_id = message.text.strip()
    if not channel_id.startswith('@'):
        msg = bot.reply_to(message, "⚠️ خطأ! يجب أن يبدأ بـ @. حاول مرة أخرى:")
        bot.register_next_step_handler(msg, save_channel_step)
        return

    set_user_channel(message.chat.id, channel_id)
    bot.send_message(message.chat.id, f"✅ **تم حفظ القناة:** {channel_id}\n🚀 يمكنك الآن إرسال الأسئلة!")

@bot.message_handler(commands=['settings'])
def show_settings(message):
    current = get_user_channel(message.chat.id)
    text = f"⚙️ **إعداداتك الحالية:**\n📍 القناة: `{current if current else 'غير محددة'}`"
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔄 تغيير القناة", callback_data="change_ch"))
    bot.send_message(message.chat.id, text, parse_mode='Markdown', reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "change_ch")
def change_channel_callback(call):
    msg = bot.send_message(call.message.chat.id, "📝 أرسل معرف القناة الجديد:")
    bot.register_next_step_handler(msg, save_channel_step)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "📜 **كيفية كتابة الأسئلة:**\n\n"
        "السؤال الأول هنا\n"
        "خيار خطأ\n"
        "<خيار صح>\n"
        "خيار خطأ آخر\n\n"
        "⚠️ اترك سطر فارغ بين كل سؤال والآخر."
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_questions(message):
    channel_id = get_user_channel(message.chat.id)
    if not channel_id:
        msg = bot.reply_to(message, "⚠️ حدد قناة أولاً:")
        bot.register_next_step_handler(msg, save_channel_step)
        return

    questions = parse_questions_universal(message.text)
    if not questions:
        bot.reply_to(message, "⚠️ التنسيق غير صحيح.")
        return

    bot.reply_to(message, f"⏳ جاري النشر...")
    for q in questions:
        try:
            bot.send_poll(chat_id=channel_id, question=q['question'], options=q['options'], 
                          type='quiz', correct_option_id=q['correct'], is_anonymous=True)
            time.sleep(2)
        except: break
    bot.send_message(message.chat.id, "✅ تم النشر.")

if __name__ == "__main__":
    init_db()
    set_bot_commands() # تفعيل الزر الجانبي وقائمة الأوامر
    Thread(target=run_web_server).start()
    print("البوت يعمل...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            time.sleep(1)
