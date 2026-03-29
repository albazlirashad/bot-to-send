import telebot
from telebot import types
import re
import time
import os
from flask import Flask, request
from dotenv import load_dotenv

# تحميل التوكن من ملف .env
load_dotenv()

# --- إعداد سيرفر Flask لضمان استمرارية الخدمة على Render بنظام Webhook ---
app = Flask(__name__)

API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
bot = telebot.TeleBot(API_TOKEN)

# مخزن مؤقت لحفظ الأسئلة قبل التأكيد (لأننا لا نستخدم قاعدة بيانات)
user_data_storage = {}

@app.route('/')
def home():
    return "Bot is Running Live!", 200

# المسار الخاص باستقبال تحديثات تليجرام
@app.route('/' + API_TOKEN, methods=['POST'])
def get_message():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        return "Forbidden", 403

# --- إعدادات البوت ---
def set_bot_commands():
    commands = [
        types.BotCommand("start", "🚀 بدء البوت / ربط القناة"),
        types.BotCommand("settings", "⚙️ إعدادات القناة"),
        types.BotCommand("help", "❓ دليل التنسيق والمساعدة")
    ]
    bot.set_my_commands(commands)

# --- منطق معالجة الأسئلة (المطور) ---
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

# --- الأوامر والردود التفاعلية ---

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
        if raw_input == '/settings': return show_settings(message, None)
        
        msg = bot.send_message(message.chat.id, "⚠️ خطأ: يرجى إرسال معرف القناة (مثلاً @channel) أولاً، أو اختر أمراً واضحاً من القائمة:")
        bot.register_next_step_handler(msg, save_channel_step)
        return

    is_not_id = not (raw_input.startswith('@') or 't.me/' in raw_input or len(raw_input.split()) == 1)
    if is_not_id:
        msg = bot.send_message(message.chat.id, "❌ عذراً، لا يمكنني قبول هذه الرسالة. أحتاج فقط إلى معرف القناة (مثلاً: @mychannel) لربط البوت:")
        bot.register_next_step_handler(msg, save_channel_step)
        return

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
        "📝 **أمثلة للتنسيق الصحيح (يمكنك النسخ والتجربة):**\n\n"
        "ما هو أسرع حيوان بري في العالم؟\n"
        "الأسد\n"
        "<الفهد>\n"
        "الغزال\n"
        "\n"
        "يُعتبر غاز ........ هو الغاز الضروري للتنفس.\n"
        "النيتروجين\n"
        "<الأكسجين>\n"
        "\n"
        "هل تشرق الشمس من جهة الغرب؟\n"
        "صح\n"
        "<خطأ>\n\n"
        "💡 **تذكير:** اترك سطرًا فارغًا بين كل سؤال والآخر."
    )
    msg = bot.send_message(message.chat.id, success_text, parse_mode='Markdown')
    # نمرر المعرف للخطوة التالية بدلاً من قاعدة البيانات
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
        "لتحويل رسائلك إلى اختبارات، اتبع هذا التنسيق بدقة:\n\n"
        "✅ **القواعد:**\n"
        "1️⃣ اترك سطرًا فارغًا بين كل سؤال والآخر.\n"
        "2️⃣ ضع الإجابة الصحيحة دائمًا بين علامتي `< >`.\n"
        "3️⃣ تأكد من إضافة البوت كمشرف (Admin) في القناة.\n\n"
        "📝 **أمثلة للتنسيق:**\n\n"
        "ما هو أكبر كوكب في مجموعتنا الشمسية؟\n"
        "المريخ\n"
        "<المشتري>\n"
        "زحل\n"
        "\n"
        "تعتبر مدينة ........ العاصمة الاقتصادية لليمن.\n"
        "<عدن>\n"
        "المكلا\n"
        "الحديدة\n"
        "\n"
        "هل الشمس كوكب؟\n"
        "صح\n"
        "<خطأ>\n\n"
        "⚠️ **تنبيه:** إذا لم ينشر البوت، يرجى مراجعة صلاحية 'نشر الرسائل' في قناتك."
    )
    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')

# --- الجزء المطور: نظام التأكيد والمعالجة الذكية للطول ---
@bot.callback_query_handler(func=lambda call: call.data in ["confirm_pub", "cancel_pub"])
def handle_publish_confirmation(call):
    chat_id = call.message.chat.id
    if chat_id not in user_data_storage:
        bot.answer_callback_query(call.id, "⚠️ انتهت الجلسة، يرجى إرسال الأسئلة مجدداً.")
        return

    if call.data == "cancel_pub":
        bot.edit_message_text("❌ تم إلغاء عملية النشر.", chat_id, call.message.message_id)
        user_data_storage.pop(chat_id, None)
        return

    questions = user_data_storage[chat_id]['questions']
    channel_id = user_data_storage[chat_id]['channel_id']
    
    bot.edit_message_text(f"⏳ جاري النشر في {channel_id}...", chat_id, call.message.message_id)
    
    sent_count = 0
    for q in questions:
        # معالجة النصوص الطويلة (قانون التجارة)
        is_too_long = len(q['question']) > 300 or any(len(opt) > 100 for opt in q['options'])
        
        try:
            if is_too_long:
                text_quiz = f"📝 **سؤال طويل:**\n\n{q['question']}\n\n"
                for idx, opt in enumerate(q['options']):
                    mark = "✅" if idx == q['correct'] else "▫️"
                    text_quiz += f"{mark} {opt}\n"
                bot.send_message(chat_id=channel_id, text=text_quiz)
            else:
                bot.send_poll(
                    chat_id=channel_id,
                    question=q['question'],
                    options=q['options'],
                    type='quiz',
                    correct_option_id=q['correct'],
                    is_anonymous=True
                )
            sent_count += 1
            time.sleep(1.5)
        except Exception:
            continue
            
    bot.send_message(chat_id, f"✅ تم نشر {sent_count} سؤال بنجاح!")
    user_data_storage.pop(chat_id, None)

@bot.message_handler(func=lambda message: True)
def handle_questions(message, channel_id=None):
    if not channel_id:
        msg = bot.reply_to(message, "⚠️ لم تربط قناة بعد. أرسل معرف قناتك الآن:")
        bot.register_next_step_handler(msg, save_channel_step)
        return

    questions = parse_questions_universal(message.text)
    if not questions:
        bot.reply_to(message, "⚠️ لم أتعرف على الأسئلة. تأكد من وضع الإجابة الصحيحة بين `< >` وسطر فارغ بين الأسئلة.")
        bot.register_next_step_handler(message, handle_questions, channel_id)
        return

    # تحليل البيانات قبل النشر (الاقتراح)
    long_q = sum(1 for q in questions if len(q['question']) > 300 or any(len(opt) > 100 for opt in q['options']))
    
    user_data_storage[message.chat.id] = {
        'questions': questions,
        'channel_id': channel_id
    }

    report = (
        f"📊 **تقرير الفحص القبل للنشر:**\n"
        f"━━━━━━━━━━━━━━\n"
        f"✅ عدد الأسئلة المكتشفة: {len(questions)}\n"
        f"📝 أسئلة عادية (Poll): {len(questions) - long_q}\n"
        f"⚠️ نصوص طويلة (Text): {long_q}\n"
        f"📍 القناة المستهدفة: {channel_id}\n"
        f"━━━━━━━━━━━━━━\n"
        f"هل تريد البدء بعملية النشر الآن؟"
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ نعم، انشر الآن", callback_data="confirm_pub"),
        types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel_pub")
    )
    bot.send_message(message.chat.id, report, parse_mode='Markdown', reply_markup=markup)
    
    # السماح بإرسال دفعة جديدة من الأسئلة في أي وقت
    bot.register_next_step_handler(message, handle_questions, channel_id)

# --- التشغيل النهائي بنظام Webhook ---
if __name__ == "__main__":
    set_bot_commands()
    
    # الحصول على رابط المشروع من Render لتعيين الويب هوك
    RENDER_URL = os.getenv('RENDER_EXTERNAL_URL')
    if RENDER_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{API_TOKEN}")
    
    # تشغيل Flask بشكل أساسي
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
