import telebot
from telebot import types
import re
import time
import os
from flask import Flask, request
from dotenv import load_dotenv

# تحميل التوكن من ملف .env
load_dotenv()

# --- إعداد سيرفر Flask (المحرك الأساسي لـ Render) ---
app = Flask(__name__)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

@app.route('/')
def home():
    return "Bot is Running Live via Webhook!", 200

# استقبال التحديثات من تليجرام
@app.route('/' + API_TOKEN, methods=['POST'])
def get_message():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Forbidden", 403

# --- إعدادات أوامر البوت ---
def set_bot_commands():
    commands = [
        types.BotCommand("start", "🚀 بدء البوت / ربط القناة"),
        types.BotCommand("settings", "⚙️ إعدادات القناة"),
        types.BotCommand("help", "❓ دليل التنسيق والمساعدة")
    ]
    bot.set_my_commands(commands)

# --- محرك تحليل الأسئلة (Universal Parser) ---
def parse_questions_universal(text):
    # التقسيم بناءً على سطر فارغ أو ترقيم أسطر
    blocks = re.split(r'\n\s*\n', text.strip())
    if len(blocks) <= 1:
        blocks = re.split(r'\n(?=\d+[\.\-\)])|^(?=\d+[\.\-\)])', text.strip())

    parsed_data = []
    for block in blocks:
        lines = [l.strip() for l in block.strip().split('\n') if l.strip()]
        if len(lines) < 2: continue

        question_raw = lines[0]
        # تنظيف أرقام الأسئلة والمراجع مثل [105]
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

# --- منطق الأوامر والتفاعل ---

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
        if raw_input == '/help': return help_command(message)
        if raw_input == '/settings': return show_settings(message)
        return

    # استخراج المعرف وتنظيفه
    if 't.me/' in raw_input:
        channel_id = '@' + raw_input.split('t.me/')[-1].split('/')[0]
    elif raw_input.startswith('@'):
        channel_id = raw_input
    else:
        channel_id = '@' + raw_input
    channel_id = channel_id.replace(' ', '')

    success_text = (
        f"✅ **تم حفظ القناة بنجاح:** {channel_id}\n\n"
        "🚀 **أرسل أسئلتك الآن ليتم نشرها فوراً!**\n\n"
        "💡 **تذكير:** اترك سطرًا فارغًا بين كل سؤال والآخر."
    )
    msg = bot.send_message(message.chat.id, success_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, handle_questions, channel_id)

@bot.message_handler(commands=['settings'])
def show_settings(message, current_id=None):
    text = f"⚙️ **إعدادات القناة:**\n📍 القناة الحالية: `{current_id if current_id else 'غير محددة'}`"
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
        "📖 **دليل التنسيق الشامل**\n\n"
        "لتحويل رسائلك إلى اختبارات، اتبع هذا التنسيق:\n"
        "1️⃣ اترك سطرًا فارغًا بين كل سؤال والآخر.\n"
        "2️⃣ ضع الإجابة الصحيحة بين علامتي `< >`.\n\n"
        "⚠️ **تنبيه:** إذا كان السؤال طويلاً جداً (أكثر من 300 حرف)، سيقوم البوت بنشره كرسالة نصية بدلاً من استطلاع لضمان عدم توقف الخدمة."
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# --- معالجة النشر الذكي (حل مشكلة السؤال 21 وما بعده) ---
def handle_questions(message, channel_id=None):
    if not channel_id:
        msg = bot.reply_to(message, "⚠️ لم تربط قناة بعد. أرسل معرف قناتك الآن:")
        bot.register_next_step_handler(msg, save_channel_step)
        return

    questions = parse_questions_universal(message.text)
    if not questions:
        bot.reply_to(message, "⚠️ لم أتعرف على الأسئلة. تأكد من وضع الإجابة الصحيحة بين `< >` وسطر فارغ.")
        bot.register_next_step_handler(message, handle_questions, channel_id)
        return

    bot.send_message(message.chat.id, f"⏳ جاري النشر في {channel_id}...")
    
    sent_count = 0
    for i, q in enumerate(questions):
        # حدود تليجرام: السؤال 300 حرف، الخيار 100 حرف
        is_too_long = len(q['question']) > 300 or any(len(opt) > 100 for opt in q['options'])
        
        try:
            if is_too_long:
                # نشر كرسالة نصية إذا تجاوز الحدود (مثل مواد القانون الطويلة)
                text_quiz = f"📝 **سؤال (نصي بسبب الطول):**\n\n{q['question']}\n\n"
                for idx, opt in enumerate(q['options']):
                    mark = "✅" if idx == q['correct'] else "▫️"
                    text_quiz += f"{mark} {opt}\n"
                bot.send_message(chat_id=channel_id, text=text_quiz)
            else:
                # نشر كاستطلاع (Quiz) طبيعي
                bot.send_poll(
                    chat_id=channel_id,
                    question=q['question'],
                    options=q['options'],
                    type='quiz',
                    correct_option_id=q['correct'],
                    is_anonymous=True
                )
            
            sent_count += 1
            time.sleep(2) # تأخير لضمان عدم الحظر

        except Exception as e:
            bot.send_message(message.chat.id, f"❌ تخطي السؤال {i+1} لوجود خطأ تقني.")
            continue
            
    if sent_count > 0:
        bot.send_message(message.chat.id, f"✅ تم الانتهاء بنجاح! تم نشر {sent_count} سؤال.")
    
    # البقاء في وضع الاستعداد لنفس القناة
    bot.register_next_step_handler(message, handle_questions, channel_id)

# --- التشغيل النهائي ---
if __name__ == "__main__":
    set_bot_commands()
    
    # ربط الويب هوك مع رابط Render التلقائي
    RENDER_URL = os.getenv('RENDER_EXTERNAL_URL')
    if RENDER_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")
        print(f"Webhook set successfully on: {RENDER_URL}")
    
    # بدء السيرفر
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
