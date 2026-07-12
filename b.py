import os
import sys
import pandas as pd
import telebot
from telebot import apihelper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# --- [حل مشكلة السيرفر والبروكسي] ---
# إجبار النظام على استخدام البروكسي المعتمد للحسابات المجانية في PythonAnywhere
apihelper.proxy = {'https': 'http://proxy.server:3128'}

# 1. إعدادات البوت الرسمية والآمنة الخاصة بك
API_TOKEN = '8739537519:AAFWVAc7JFiA_BAl1VFAmkjBUtH3SiABEvc'
ADMIN_ID = 224931513  # معرفك الرقمي كمشرف لحساب @ll8lll

bot = telebot.TeleBot(API_TOKEN)

# مسارات الملفات على جهازك / السيرفر
FILE_PATH_CODES = r"/home/KARRAR123/ahussein/b1.py" 
# تم تعديل اسم الملف هنا إلى الاسم الجديد لتفادي مشكلة مسارات الحروف العربية
FILE_PATH_EXCEL = r"/home/KARRAR123/ahussein/jard2023.xlsx" 

# مصفوفات مؤقتة في الذاكرة لتتبع حالة المستخدمين وطرق البحث
ACTIVATED_USERS = set()
USERS_AWAITING_CODE = set()
USER_SEARCH_MODE = {}  # لتخزين وضع البحث لكل مستخدم (اسم أو سيريال)

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
            # قراءة الأسطر البرمجية الصالحة فقط وتجاهل أي نصوص عشوائية سببت خطأ سابقاً
            code_content = "".join([line for line in lines if "ALLOWED_CODES" in line or line.strip().startswith("[") or line.strip().endswith("]")])
            exec(code_content, namespace)
        return [str(code) for code in namespace.get("ALLOWED_CODES", [])]
    except Exception as e:
        print(f"⚠️ خطأ في قراءة ملف الأكواد: {e}")
        return []

def add_code_to_file(new_code):
    codes = get_allowed_codes()
    if str(new_code) not in codes:
        codes.append(str(new_code))
        with open(FILE_PATH_CODES, "w", encoding="utf-8") as f:
            f.write(f"ALLOWED_CODES = {codes}\n")

# دالة موحدة لعرض خيارات البحث للمستخدمين المصرح لهم
def show_search_options(chat_id, user_name):
    keyboard = InlineKeyboardMarkup()
    btn_name = InlineKeyboardButton("🔍 البحث باسم الجهاز", callback_data='search_by_name')
    btn_serial = InlineKeyboardButton("🔢 البحث بالرقم التسلسلي", callback_data='search_by_serial')
    keyboard.add(btn_name, btn_serial)
    
    bot.send_message(
        chat_id,
        f"👋 مرحباً بك يا {user_name} في بوت مستشفى الحسين التعليمي! 🏥\n\n"
        "⚙️ الرجاء اختيار طريقة البحث من الأزرار أدناه:",
        reply_markup=keyboard
    )

# --- معالجة الأوامر والرسائل ---

# عند إرسال أمر /start
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    if user_id in USER_SEARCH_MODE:
        del USER_SEARCH_MODE[user_id]

    if user_id == ADMIN_ID:
        bot.send_message(user_id, "👑 مرحباً أيها المشرف الحسين! أنت تملك الصلاحية الكاملة لإدارة البوت الآن.")
        show_search_options(message.chat.id, user_name)
        return

    if user_id in ACTIVATED_USERS:
        show_search_options(message.chat.id, user_name)
        return

    bot.reply_to(message, "🔒 عذراً، هذا النظام مغلق ومحمي.\n🔑 يرجى إرسال كود التفعيل الخاص بك للدخول:")
    USERS_AWAITING_CODE.add(user_id)


# معالجة ضغطات الأزرار التفاعلية
@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if call.data.startswith(('accept_', 'reject_')):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "❌ عذراً، أنت لست المشرف المصرح له!", show_alert=True)
            return

        data_parts = call.data.split('_')
        action = data_parts[0]
        target_user_id = int(data_parts[1])

        if action == "accept":
            target_code = data_parts[2]
            add_code_to_file(target_code)
            ACTIVATED_USERS.add(target_user_id)
            if target_user_id in USERS_AWAITING_CODE:
                USERS_AWAITING_CODE.remove(target_user_id)
            
            bot.edit_message_text(f"✅ تم قبول المستخدم بنجاح، وتم حفظ الكود `{target_code}` في الملف تلقائياً.", chat_id, message_id)
            bot.send_message(target_user_id, "🎉 مرحباً بك! لقد وافق المشرف على طلبك واعتمد الكود الخاص بك بنجاح.")
            show_search_options(target_user_id, call.message.reply_to_message.from_user.first_name if call.message.reply_to_message else "المستخدم")
            
        elif action == "reject":
            if target_user_id in USERS_AWAITING_CODE:
                USERS_AWAITING_CODE.remove(target_user_id)
            bot.edit_message_text("❌ تم رفض طلب الدخول هذا.", chat_id, message_id)
            bot.send_message(target_user_id, "🚫 عذراً، تم رفض طلب انضمامك ولم يتم اعتماد الكود من قبل إدارة المستشفى.")
        return

    if user_id != ADMIN_ID and user_id not in ACTIVATED_USERS:
        bot.answer_callback_query(call.id, "🔒 يجب التفعيل أولاً والاستحصال على الموافقة.", show_alert=True)
        return

    bot.answer_callback_query(call.id)
    if call.data == 'search_by_name':
        USER_SEARCH_MODE[user_id] = 'name'
        bot.edit_message_text("📝 رجاءً أرسل **اسم الجهاز** (أو جزءاً منه) الموجود في العمود B:", chat_id, message_id, parse_mode="Markdown")
    elif call.data == 'search_by_serial':
        USER_SEARCH_MODE[user_id] = 'serial'
        bot.edit_message_text("🔢 رجاءً أرسل **الرقم التسلسلي** المطابق تماماً والموجود في العمود E:", chat_id, message_id, parse_mode="Markdown")


# استقبال الرسائل النصية والتعامل معها
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    text_input = message.text.strip()

    if user_id != ADMIN_ID and user_id in USERS_AWAITING_CODE:
        allowed_codes = get_allowed_codes()

        if text_input in allowed_codes:
            ACTIVATED_USERS.add(user_id)
            USERS_AWAITING_CODE.remove(user_id)
            bot.reply_to(message, "✅ الكود صحيح ومعتمد مسبقاً! تم السماح لك بالدخول واستخدام النظام.")
            show_search_options(message.chat.id, user_name)
            return

        bot.reply_to(message, "⏳ هذا الكود غير مسجل مسبقاً.\n📬 تم إرسال طلب تفعيل إلى المشرف للمراجعة، يرجى الانتظار...")
        
        markup = InlineKeyboardMarkup()
        approve_btn = InlineKeyboardButton("قبول ✅", callback_data=f"accept_{user_id}_{text_input}")
        reject_btn = InlineKeyboardButton("رفض ❌", callback_data=f"reject_{user_id}")
        markup.add(approve_btn, reject_btn)
        
        user_info = f"👤 **طلب دخول جديد لبوت مستشفى الحسين:**\n\n🔹 **الاسم:** {user_name}\n🔹 **اليوزر:** @{message.from_user.username}\n🔹 **الآيدي:** `{user_id}`\n\n🔑 **الكود المُدخل:** `{text_input}`"
        bot.send_message(ADMIN_ID, user_info, reply_markup=markup, parse_mode="Markdown")
        return

    if user_id != ADMIN_ID and user_id not in ACTIVATED_USERS:
        bot.reply_to(message, "🔒 الوصول ممنوع. يجب عليك إدخال كود تفعيل معتمد أولاً عبر إرسال /start.")
        USERS_AWAITING_CODE.add(user_id)
        return

    search_mode = USER_SEARCH_MODE.get(user_id)
    
    if not search_mode:
        bot.reply_to(message, "⚠️ الرجاء اختيار طريقة البحث أولاً من الخيارات المتاحة.")
        show_search_options(message.chat.id, user_name)
        return

    if not os.path.exists(FILE_PATH_EXCEL):
        bot.reply_to(message, f"❌ عذراً، ملف جرد الإكسل غير موجود في المسار المحدد: {FILE_PATH_EXCEL}")
        return

    bot.reply_to(message, "🔍 جاري البحث في قاعدة البيانات وإحضار كافة النتائج المطابقة...")

    try:
        df = pd.read_excel(FILE_PATH_EXCEL, skiprows=2, dtype=str)
        df.columns = df.columns.str.strip()
        result = pd.DataFrame()

        if search_mode == 'serial':
            if len(df.columns) < 5:
                bot.reply_to(message, "❌ خطأ: ملف الإكسل يحتوي على أقل من 5 أعمدة، لا يمكن الوصول للعمود E.")
                return
            serial_col = df.columns[4]
            df[serial_col] = df[serial_col].str.strip()
            result = df[df[serial_col] == text_input]

        elif search_mode == 'name':
            if len(df.columns) < 2:
                bot.reply_to(message, "❌ خطأ: ملف الإكسل يحتوي على أقل من عمودين، لا يمكن الوصول للعمود B.")
                return
            name_col = df.columns[1]
            result = df[df[name_col].str.contains(text_input, case=False, na=False, regex=False)]

        if not result.empty:
            total_found = len(result)
            bot.send_message(message.chat.id, f"🎉 تم العثور على ({total_found}) من النتائج المطابقة:")

            for idx, row in result.iterrows():
                response_text = f"📋 **بيانات الجهاز رقم {idx + 1}:**\n"
                response_text += "━━━━━━━━━━━━━━━━━━━━\n"
                for column, value in row.items():
                    if pd.notna(value) and str(value).lower() != 'nan':
                        response_text += f"🔹 **{column}:** {value}\n"
                response_text += "━━━━━━━━━━━━━━━━━━━━"
                bot.send_message(message.chat.id, response_text, parse_mode="Markdown")
        else:
            bot.reply_to(message, f"❌ لم يتم العثور على أي نتائج تطابق: `{text_input}`")

    except Exception as e:
        bot.reply_to(message, f"⚠️ حدث خطأ أثناء معالجة البيانات: {e}")

    if user_id in USER_SEARCH_MODE:
        del USER_SEARCH_MODE[user_id]
    
    bot.send_message(message.chat.id, "🔄 لإجراء بحث جديد، اضغط على /start")

# تشغيل البوت
print("🚀 البوت يعمل الآن ومحمى بنظام التفعيل ومربوط بملف الإكسل بنجاح...")
bot.polling(none_stop=True)
