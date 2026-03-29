import os
import re
import time
from flask import Flask, request
import telebot
from telebot import types
from dotenv import load_dotenv

# تحميل الإعدادات
load_dotenv()
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)
app = Flask(__name__)

# --- إعداد سيرفر Flask لضمان استمرارية الخدمة ---
@app.route('/')
def home():
    return "Bot is Running Live!", 200

@app.route('/' + API_TOKEN, methods=['POST'])
def get_message():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    return "Forbidden", 403

# --- منطق معالجة الأسئلة المطور (تجاهل الأخطاء والاستمرار) ---
def parse_question_smart(text_block):
    # البحث عن الإجابة الصحيحة بين < >
    match_correct = re.search(r'<(.*?)>', text_block)
    if not match_correct:
        return None
    
    correct_answer = match_correct.group(1).strip()
    clean_block = text_block.replace(f"<{correct_answer}>", correct_answer)
    
    # تقسيم النص لأسطر وتنظيفها
    lines = [l.strip() for l in clean_block.split('\n') if l.strip()]
    if len(lines) < 2:
        return None

    question_text = re.sub(r'^\d+[\s\.\-\)]+', '', lines[0]).strip()
    options = lines[1:]

    # التحقق من حدود تيليجرام (السؤال < 300 حرف، الخيارات < 10)
    if len(question_text) > 300 or len(options) > 10 or len(options) < 2:
        return "TOO_BIG_OR_INVALID"

    try:
        correct_index = options.index(correct_answer)
        return {"question": question_text, "options": options, "correct": correct_index}
    except ValueError:
        return None

# --- الأوامر والرسائل (نفس نصوصك الأصلية) ---

@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = (
        "✨ ** مرحباً بك في نظام النشر الذكي** ✨\n"
        "﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏\n\n"
        "أداة متخصصة لتحويل نصوص الأسئلة العادية إلى **اختبارات تفاعلية (Quizzes)** احترافية في قناتك بضغطة واحدة. 🚀\n\n"
        "📢 **خطوات البدء السريع:**\n"
        "┌ 1️⃣ أضف البوت **مشرفاً (Admin)**.\n"
        "└ 2️⃣ فعّل صلاحية **نشر الرسائل**.\n\n"
        "📜 **قواعد التنسيق:**\n"
        "• اترك **سطراً فارغاً** بين كل سؤال والآخر.\n"
        "• ضع الإجابة الصحيحة بين علامتي **`< >`**.\n\n"
        "﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏﹏\n"
        "📍 **للبدء، أرسل الآن معرف قناتك (مثال: @mychannel):**"
    )
    msg = bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, save_channel_step)

def save_channel_step(message):
    raw_input = message.text.strip()
    if raw_input.startswith('/'):
        if raw_input == '/start': return start_command(message)
        return
    
    # تنظيف معرف القناة
    channel_id = raw_input if raw_input.startswith('@') else '@' + raw_input
    
    success_text = (
        f"✅ **تم حفظ القناة بنجاح:** {channel_id}\n\n"
        "🚀 **أرسل أسئلتك الآن ليتم نشرها فوراً!**\n\n"
        "💡 **تذكير:** اترك سطرًا فارغًا بين كل سؤال والآخر."
    )
    msg = bot.send_message(message.chat.id, success_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, handle_questions, channel_id)

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = (
        "📖 **دليل التنسيق الشامل**\n\n"
        "1️⃣ اترك سطرًا فارغًا بين كل سؤال والآخر.\n"
        "2️⃣ ضع الإجابة الصحيحة دائماً بين علامتي `< >`.\n\n"
        "📝 **مثال:**\n"
        "ما هو عاصمة اليمن؟\n"
        "عدن\n"
        "<صنعاء>\n"
        "تعز"
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def handle_questions(message, channel_id=None):
    if not channel_id:
        msg = bot.reply_to(message, "⚠️ لم تربط قناة بعد. أرسل معرف قناتك الآن:")
        bot.register_next_step_handler(msg, save_channel_step)
        return

    # تقسيم الرسالة الكبيرة إلى كتل أسئلة
    blocks = re.split(r'\n\s*\n', message.text.strip())
    bot.send_message(message.chat.id, f"⏳ جاري معالجة {len(blocks)} سؤال ونشرها في {channel_id}...")
    
    sent_count = 0
    skipped_count = 0

    for block in blocks:
        data = parse_question_smart(block)
        
        if data == "TOO_BIG_OR_INVALID":
            skipped_count += 1
            continue # يتجاهل السؤال الكبير ويستمر للباقي
            
        if data:
            try:
                bot.send_poll(
                    chat_id=channel_id,
                    question=data['question'],
                    options=data['options'],
                    type='quiz',
                    correct_option_id=data['correct'],
                    is_anonymous=True
                )
                sent_count += 1
                time.sleep(1) # لتجنب سبام تيليجرام
            except Exception:
                skipped_count += 1
        else:
            skipped_count += 1

    result_msg = f"✅ تم نشر {sent_count} سؤال بنجاح!"
    if skipped_count > 0:
        result_msg += f"\n⚠️ تم تجاهل {skipped_count} سؤال (بسبب حجمها أو خطأ في التنسيق)."
    
    bot.send_message(message.chat.id, result_msg)
    # الاستمرار في نفس القناة لاستقبال الدفعة القادمة
    bot.register_next_step_handler(message, handle_questions, channel_id)

# --- التشغيل النهائي ---
if __name__ == "__main__":
    bot.set_my_commands([
        types.BotCommand("start", "🚀 بدء البوت / ربط القناة"),
        types.BotCommand("help", "❓ دليل التنسيق")
    ])

    RENDER_URL = os.getenv('RENDER_EXTERNAL_URL')
    if RENDER_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
