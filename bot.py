import telebot
import re
import time
import os
from threading import Thread
from flask import Flask
from dotenv import load_dotenv

# تحميل المتغيرات البيئية من ملف .env (للتطوير المحلي)
load_dotenv()

# --- إعداد خادم ويب بسيط لإبقاء ريندر مستيقظاً ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Running Live!"

def run_web_server():
    # ريندر يستخدم المنفذ 10000 أو المنفذ المحدد في المتغيرات البيئية
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

# --- بيانات البوت والقناة ---
# جلب التوكن من المتغيرات البيئية (أكثر أماناً)
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = '@jjjjakjdopak'

bot = telebot.TeleBot(API_TOKEN)

def parse_questions_universal(text):
    # تقسيم النص بناءً على أسطر فارغة أو ترقيم
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
def welcome(message):
    welcome_text = (
        "👋 **أهلاً بك في بوت نشر الاختبارات التفاعلية**\n\n"
        f"📍 **يتم النشر تلقائياً في:** {CHANNEL_ID}\n\n"
        "📜 **شروط وقواعد إرسال الأسئلة:**\n"
        "1️⃣ **الكمية:** يمكنك إرسال عدة أسئلة في رسالة واحدة.\n"
        "2️⃣ **الفصل:** اترك سطر فارغ بين كل سؤال والآخر.\n"
        "3️⃣ **الإجابة:** ضع الإجابة الصحيحة بين `< >`."
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_questions(message):
    questions = parse_questions_universal(message.text)
    if not questions:
        bot.reply_to(message, "⚠️ لم يتم التعرف على الأسئلة. تأكد من وضع الإجابة بين < > وفصل الأسئلة.")
        return

    bot.reply_to(message, f"⏳ جاري النشر...")
    sent_count = 0
    for q in questions:
        try:
            bot.send_poll(
                chat_id=CHANNEL_ID,
                question=q['question'],
                options=q['options'],
                type='quiz',
                correct_option_id=q['correct'],
                is_anonymous=True
            )
            sent_count += 1
            time.sleep(2) # حماية من الحظر (Flood protection)
        except Exception:
            pass

    bot.send_message(message.chat.id, f"✅ تم نشر {sent_count} سؤال بنجاح.")

# --- تشغيل البوت مع السيرفر ---
if __name__ == "__main__":
    # تشغيل خادم الويب في خيط منفصل
    Thread(target=run_web_server).start()
    
    print("البوت يعمل الآن...")
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)