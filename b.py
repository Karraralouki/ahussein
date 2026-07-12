import os
import sys
import time
import pandas as pd
import telebot
from telebot import apihelper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- [تعديل البروكسي الشامل] ---
apihelper.proxy = {
    'http': 'http://proxy.server:3128',
    'https': 'http://proxy.server:3128'
}

API_TOKEN = '8739537519:AAFWVAc7JFiA_BAl1VFAmkjBUtH3SiABEvc'
ADMIN_ID = 224931513  # معرفك الرقمي كمشرف

bot = telebot.TeleBot(API_TOKEN)

# المسارات الافتراضية داخل السيرفر
FILE_PATH_CODES = r"/home/KARRAR123/ahussein/b1.py" 
FILE_PATH_EXCEL = r"/home/KARRAR123/ahussein/jard2023.xlsx" 

ACTIVATED_USERS = set()
USERS_AWAITING_CODE = set()
USER_SEARCH_MODE = {}

# --- دالات إدارة نظام الأكواد والحماية ---
def get_allowed_codes():
    if not os.path.exists(FILE_PATH_CODES):
        with open(FILE_PATH_CODES, "w", encoding="utf-8") as f:
            f.write("ALLOWED_CODES = []\n")
        return []
    try:
        namespace = {}
        with open(FILE_PATH_CODES, "r", encoding="utf-8") as f:
            lines = f.readlines()
            code_content = "".join([line for line in lines if "ALLOWED_CODES" in line or line.strip().startswith("[") or line.strip().endswith("]")])
            exec(code_content, namespace)
        return [str(code) for code in namespace.get("ALLOWED_CODES", [])]
    except Exception:
        return []

def add_code_to_file(new_code):
    codes = get_allowed_codes()
    if str(new_code) not in codes:
        codes.append(str(new_code))
        with open(FILE_PATH_CODES, "w", encoding="utf-8") as f:
            f.write(f"ALLOWED_CODES = {codes}\n")

def show_search_options(chat_id, user_name):
    keyboard = InlineKeyboardMarkup()
    btn_name = InlineKeyboardButton("🔍 البحث باسم الجهاز", callback_data='search_by_name')
    btn_serial = InlineKeyboardButton("🔢 البحث بالرقم التسلسلي", callback_data='search_by_serial')
    keyboard.add(btn_name, btn_serial)
    bot.send_message(chat_id, f"👋 مرحباً بك يا {user_name}!\n⚙️ اختر طريقة البحث:", reply_markup=keyboard)

# --- معالجة الأوامر والرسائل ---
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    if user_id in USER_SEARCH_MODE: del USER_SEARCH_MODE[user_id]
    if user_id == ADMIN_ID or user_id in ACTIVATED_USERS:
        show_search_options(message.chat.id, user_name)
        return
    bot.reply_to(message, "🔒 النظام محمي. يرجى إرسال كود التفعيل:")
    USERS_AWAITING_CODE.add(user_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data.startswith(('accept_', 'reject_')):
        if user_id != ADMIN_ID: return
        data_parts = call.data.split('_')
        action, target_user_id = data_parts[0], int(data_parts[1])
        if action == "accept":
            target_code = data_parts[2]
            add_code_to_file(target_code)
            ACTIVATED_USERS.add(target_user_id)
            if target_user_id in USERS_AWAITING_CODE: USERS_AWAITING_CODE.remove(target_user_id)
            bot.edit_message_text("✅ تم قبول المستخدم وحفظ الكود.", chat_id, message_id)
            bot.send_message(target_user_id, "🎉 وافق المشرف على طلبك!")
            show_search_options(target_user_id, "المستخدم")
        elif action == "reject":
            if target_user_id in USERS_AWAITING_CODE: USERS_AWAITING_CODE.remove(target_user_id)
            bot.edit_message_text("❌ تم رفض الطلب.", chat_id, message_id)
        return

    bot.answer_callback_query(call.id)
    if call.data == 'search_by_name':
        USER_SEARCH_MODE[user_id] = 'name'
        bot.edit_message_text("📝 أرسل **اسم الجهاز** (العمود B):", chat_id, message_id, parse_mode="Markdown")
    elif call.data == 'search_by_serial':
        USER_SEARCH_MODE[user_id] = 'serial'
        bot.edit_message_text("🔢 أرسل **الرقم التسلسلي** (العمود E):", chat_id, message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text_input = message.text.strip()

    if user_id != ADMIN_ID and user_id in USERS_AWAITING_CODE:
        if text_input in get_allowed_codes():
            ACTIVATED_USERS.add(user_id)
            USERS_AWAITING_CODE.remove(user_id)
            show_search_options(message.chat.id, message.from_user.first_name)
        else:
            bot.reply_to(message, "⏳ كود غير مسجل. تم إرسال طلب للمشرف...")
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("قبول ✅", callback_data=f"accept_{user_id}_{text_input}"), InlineKeyboardButton("رفض ❌", callback_data=f"reject_{user_id}"))
            bot.send_message(ADMIN_ID, f"🔑 طلب تفعيل بكود: `{text_input}`", reply_markup=markup, parse_mode="Markdown")
        return

    search_mode = USER_SEARCH_MODE.get(user_id)
    if not search_mode:
        show_search_options(message.chat.id, message.from_user.first_name)
        return

    actual_path = FILE_PATH_EXCEL
    if not os.path.exists(actual_path):
        base_dir = "/home/KARRAR123/"
        found_files = []
        for root, dirs, files in os.walk(base_dir):
            for file in files:
                if file.endswith(('.xlsx', '.xls')):
                    found_files.append(os.path.join(root, file))
        
        error_msg = f"❌ الملف غير موجود في المسار:\n`{FILE_PATH_EXCEL}`\n\n"
        if found_files:
            error_msg += "🔍 **الملفات المتاحة بحسابك:**\n"
            for f_path in found_files: error_msg += f"📍 `{f_path}`\n"
        bot.reply_to(message, error_msg, parse_mode="Markdown")
        return

    bot.reply_to(message, "🔍 جاري البحث في قاعدة البيانات...")

    try:
        df = pd.read_excel(actual_path, skiprows=2, dtype=str)
        df.columns = df.columns.str.strip()
        result = pd.DataFrame()

        if search_mode == 'serial':
            serial_col = df.columns[4]
            result = df[df[serial_col].str.strip() == text_input]
        elif search_mode == 'name':
            name_col = df.columns[1]
            result = df[df[name_col].str.contains(text_input, case=False, na=False, regex=False)]

        if not result.empty:
            bot.send_message(message.chat.id, f"🎉 تم العثور على ({len(result)}) نتائج:")
            for idx, row in result.iterrows():
                response_text = f"📋 **بيانات الجهاز:**\n━━━━━━━━━━━━━━━━━━━━\n"
                for col, val in row.items():
                    if pd.notna(val) and str(val).lower() != 'nan':
                        response_text += f"🔹 **{col}:** {val}\n"
                response_text += "━━━━━━━━━━━━━━━━━━━━"
                bot.send_message(message.chat.id, response_text, parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ لم يتم العثور على نتائج لـ: `{text_input}`")

    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ في القراءة: {e}")

    if user_id in USER_SEARCH_MODE: del USER_SEARCH_MODE[user_id]
    bot.send_message(message.chat.id, "🔄 للبحث مجدداً اضغط /start")

# --- [نظام تشغيل حديدي مضاد لتعطيل البروكسي] ---
print("🚀 جاري بدء تشغيل البوت بحماية البروكسي الحديدية المحدثة...")
while True:
    try:
        # استخدام دالة infinity_polling لمنع التحقق الأولي المخنوق من البروكسي والاستمرار بالعمل فوراً
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"⚠️ البروكسي يواجه ضغطاً مؤقتاً (503)، سيتم إعادة المحاولة تلقائياً بعد 10 ثوانٍ...")
        time.sleep(10)
