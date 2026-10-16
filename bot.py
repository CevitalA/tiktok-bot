import os
import sys
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
    FSInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession

import database
import excel_parser

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

BOT_TOKEN = os.getenv("BOT_TOKEN", "8881972676:AAFbhVZWztH9JKit5EHXbPN2sSeJsGiJYlQ")
# اكتشاف رابط Railway تلقائياً إذا كان متاحاً
_railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN") or os.getenv("RAILWAY_STATIC_URL")
if _railway_domain:
    _auto_url = f"https://{_railway_domain}" if not _railway_domain.startswith("http") else _railway_domain
else:
    _auto_url = "https://your-domain.com"

WEBAPP_URL = os.getenv("WEBAPP_URL", _auto_url)
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "AboHamdi")
WHATSAPP_URL = os.getenv("WHATSAPP_URL", "https://wa.me/201011055811")
WHATSAPP_PHONE = os.getenv("WHATSAPP_PHONE", "+201011055811")

admin_ids_raw = os.getenv("ADMIN_IDS", "1310039772")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()]
if 1310039772 not in ADMIN_IDS:
    ADMIN_IDS.append(1310039772)

# دعم بروكسي PythonAnywhere التلقائي للحسابات المجانية
PROXY_URL = os.getenv("TELEGRAM_PROXY")
if not PROXY_URL:
    home_dir = os.path.expanduser("~")
    if "pythonanywhere" in os.getenv("PYTHONANYWHERE_DOMAIN", "") or "amon141" in home_dir or os.path.exists("/var/log/pythonanywhere"):
        PROXY_URL = "http://proxy.server:3128"

if PROXY_URL:
    logging.info(f"🌐 الاتصال بسيرفرات تليجرام عبر بروكسي PythonAnywhere: {PROXY_URL}")
    session = AiohttpSession(proxy=PROXY_URL)
    bot = Bot(token=BOT_TOKEN, session=session)
else:
    bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class Form(StatesGroup):
    waiting_for_key = State()

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def get_main_keyboard(user_id: int, is_sub_active: bool) -> InlineKeyboardMarkup:
    buttons = []
    
    if is_sub_active or is_admin(user_id):
        buttons.append([
            InlineKeyboardButton(
                text="🏆 فتح تطبيق الليجات (Mini App)",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        ])
        buttons.append([
            InlineKeyboardButton(text="📊 تفاصيل اشتراكي", callback_data="check_status"),
            InlineKeyboardButton(text="🎟 كود تفعيل", callback_data="prompt_redeem")
        ])
        buttons.append([
            InlineKeyboardButton(text="💬 دعم واتساب (أبو حمدي)", url=WHATSAPP_URL)
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="💬 تواصل واتساب للاشتراك", url=WHATSAPP_URL)
        ])
        buttons.append([
            InlineKeyboardButton(text="🎟 إدخال كود التفعيل", callback_data="prompt_redeem"),
            InlineKeyboardButton(text="🔄 فحص الاشتراك", callback_data="check_status")
        ])
        
    if is_admin(user_id):
        buttons.append([
            InlineKeyboardButton(text="⚙️ لوحة تحكم الأدمن (أبو حمدي)", callback_data="admin_panel")
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = message.from_user
    user_id = user.id
    username = user.username or ""
    user_last = user.last_name or ''
    full_name = f"{user.first_name} {user_last}".strip()
    
    database.get_or_create_user(user_id, username, full_name, is_admin(user_id))
    sub = database.check_subscription(user_id, ADMIN_IDS)
    
    if sub["is_active"]:
        text = (
            f"مرحباً بك يا <b>{user.first_name}</b> في بوت دوريات تيك توك لايف! 🏆\n\n"
            f"👑 <b>تطوير: أبو حمدي (Abo Hamdi)</b>\n"
            f"✅ <b>حالة الاشتراك:</b> مفعّل\n"
            f"📅 <b>ينتهي في:</b> <code>{sub['end_date']}</code>\n"
            f"⏳ <b>المتبقي:</b> {sub['days_left']} يوم و {sub.get('hours_left', 0)} ساعة\n\n"
            f"اضغط على الزر بالأسفل لفتح تطبيق الليجات مباشرة وتصفح الحسابات المصنفة 👇"
        )
    else:
        text = (
            f"أهلاً بك يا <b>{user.first_name}</b> في بوت دوريات تيك توك لايف 👋\n"
            f"👑 <b>إدارة وتطوير: أبو حمدي</b>\n\n"
            f"هذا البوت مخصص للمشتركين لتصفح وفرز دوريات تيك توك لايف الرسمية (من A1 حتى D5) مع الأرباح والألماس واليوزرات كاملة.\n\n"
            f"🔒 <b>حسابك غير مفعل حالياً</b>\n"
            f"🆔 <b>معرّفك (User ID):</b> <code>{user_id}</code>\n\n"
            f"<b>طرق التفعيل والاشتراك:</b>\n"
            f"1️⃣ اضغط على زر <b>تواصل واتساب للاشتراك</b> أو راسلنا على:\n"
            f"   📱 <code>{WHATSAPP_PHONE}</code>\n"
            f"2️⃣ أو إذا كان معك كود اشتراك اضغط على <b>إدخال كود التفعيل</b>."
        )
        
    await message.answer(text, parse_mode="HTML", reply_markup=get_main_keyboard(user_id, sub["is_active"]))

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    sub = database.check_subscription(message.from_user.id, ADMIN_IDS)
    if sub["is_active"]:
        msg = (
            f"📊 <b>تفاصيل اشتراكك:</b>\n\n"
            f"• الحالة: 🟢 مفعّل\n"
            f"• تاريخ الانتهاء: <code>{sub['end_date']}</code>\n"
            f"• المتبقي: <b>{sub['days_left']} يوم</b>\n\n"
            f"لأي استفسار يمكنك التواصل مع الدعم: {WHATSAPP_URL}"
        )
    else:
        msg = (
            f"📊 <b>تفاصيل اشتراكك:</b>\n\n"
            f"• الحالة: 🔴 غير مفعّل أو منتهي\n"
            f"• المعرف الخاص بك: <code>{message.from_user.id}</code>\n\n"
            f"للاشتراك والتجديد تواصل واتساب: {WHATSAPP_URL}"
        )
    await message.answer(msg, parse_mode="HTML")

@dp.message(Command("redeem"))
async def cmd_redeem(message: types.Message):
    raw_text = message.text or ""
    code = database.clean_license_key(raw_text)
    if not code or code == "REDEEM":
        await message.answer("⚠️ <b>يرجى كتابة الكود بعد الأمر، مثال:</b>\n<code>/redeem TIK-30D-XXXXXX</code>", parse_mode="HTML")
        return
        
    res = database.redeem_license_key(message.from_user.id, code)
    sub = database.check_subscription(message.from_user.id, ADMIN_IDS)
    await message.answer(
        res["message"],
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id, sub['is_active'])
    )

@dp.callback_query(F.data == "prompt_redeem")
async def cb_prompt_redeem(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer(
        "🎟 <b>أرسل الآن كود التفعيل المخصص لك:</b>\n\n💡 <i>فقط الصق الكود هنا في المحادثة مباشرة (مثال: <code>TIK-30D-XXXXXX</code>) وسيتم تفعيل حسابك فوراً!</i>",
        parse_mode="HTML"
    )
    await state.set_state(Form.waiting_for_key)

@dp.message(Form.waiting_for_key)
async def process_redeem_key(message: types.Message, state: FSMContext):
    code = database.clean_license_key(message.text or "")
    await state.clear()
    res = database.redeem_license_key(message.from_user.id, code)
    sub = database.check_subscription(message.from_user.id, ADMIN_IDS)
    await message.answer(
        res["message"],
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.from_user.id, sub['is_active'])
    )

@dp.message(F.text & ~F.text.startswith("/"))
async def handle_direct_text(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    matched_key = database.clean_license_key(text)
    
    if "TIK-" in matched_key:
        await state.clear()
        res = database.redeem_license_key(message.from_user.id, matched_key)
        sub = database.check_subscription(message.from_user.id, ADMIN_IDS)
        await message.answer(
            res["message"],
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.from_user.id, sub['is_active'])
        )
        return
        
    lower_t = text.lower()
    if any(w in lower_t for w in ["تفعيل", "كود", "اشتراك", "شفرة", "رمز"]):
        await message.answer(
            f"🎟 <b>أهلاً بك! لتفعيل اشتراكك:</b>\nفقط أرسل كود التفعيل مباشرة في المحادثة (مثال: <code>TIK-30D-XXXXXX</code>) وسيتفعل حسابك فوراً.\n\nإذا لم يكن لديك كود تفعيل، يمكنك التواصل مع <b>أبو حمدي</b> عبر واتساب للاشتراك:\n{WHATSAPP_URL}",
            parse_mode="HTML"
        )
        await state.set_state(Form.waiting_for_key)
        return


@dp.callback_query(F.data == "check_status")
async def cb_check_status(callback: types.CallbackQuery):
    await callback.answer()
    sub = database.check_subscription(callback.from_user.id, ADMIN_IDS)
    if sub["is_active"]:
        await callback.message.answer(
            f"🟢 <b>اشتراكك مفعّل بنجاح!</b>\nينتهي في: {sub['end_date']} ({sub['days_left']} يوم متبقي)",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(callback.from_user.id, True)
        )
    else:
        await callback.message.answer(
            f"🔴 <b>اشتراكك غير مفعّل بعد</b>\nمعرّفك: <code>{callback.from_user.id}</code>\n\nللاشتراك عبر الواتساب: {WHATSAPP_URL}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(callback.from_user.id, False)
        )

# ----------------- خاصية رفع ملف الإكسل (للأدمن فقط) -----------------

@dp.message(F.document)
async def handle_admin_excel_upload(message: types.Message):
    user_id = message.from_user.id
    doc = message.document
    filename = doc.file_name or ""
    
    if not (filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls") or filename.lower().endswith(".csv")):
        return

    if not is_admin(user_id):
        await message.answer(f"⚠️ <b>عذراً يا {message.from_user.first_name}!</b>\nخاصية رفع وتحديث ملفات الإكسل مخصصة لحساب الأدمن فقط.\n\n🆔 معرفك الحالي: <code>{user_id}</code>\nإذا كنت أنت صاحب البوت، تأكد من إضافة هذا المعرف إلى <code>ADMIN_IDS</code> في إعدادات Railway.", parse_mode="HTML")
        return

    doc = message.document
    filename = doc.file_name or ""
    
    if not (filename.endswith(".xlsx") or filename.endswith(".xls") or filename.endswith(".csv")):
        await message.answer("⚠️ يرجى رفع ملف إكسل بصيغة <code>.xlsx</code> أو <code>.xls</code>", parse_mode="HTML")
        return

    wait_msg = await message.answer("⏳ <b>جاري تحميل وقراءة ملف الإكسل وتحديث قاعدة البيانات...</b>", parse_mode="HTML")
    
    temp_dir = os.path.join(os.path.dirname(__file__), "data", "temp_uploads")
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, filename)

    try:
        file = await bot.get_file(doc.file_id)
        await bot.download_file(file.file_path, destination=file_path)

        summary = excel_parser.parse_excel_file(file_path)

        report = (
            f"✅ <b>تم تحديث قاعدة بيانات الليجات بنجاح يا أبو حمدي!</b> 🎉\n\n"
            f"📊 <b>ملخص البيانات المعالجة:</b>\n"
            f"• 👥 إجمالي الحسابات: <b>{summary['total_accounts']} حساب</b>\n"
            f"• 🏆 عدد الليجات النشطة: <b>{len(summary['active_leagues'])} ليج</b>\n"
            f"• 💎 إجمالي الألماس: <b>{summary['total_diamonds']:,}</b>\n"
            f"• 💰 إجمالي الأرباح المتوقعة: <b>${summary['total_earnings']:,.2f}</b>\n\n"
            f"📌 الليجات المحدثة:\n<code>{', '.join(summary['active_leagues'])}</code>\n\n"
            f"🚀 أصبح التحديث متاحاً الآن لجميع المشتركين داخل التطبيق فوراً!"
        )
        await wait_msg.edit_text(report, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Error parsing excel: {e}")
        await wait_msg.edit_text(f"❌ <b>حدث خطأ أثناء قراءة الملف:</b>\n<code>{str(e)}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass

# ----------------- أوامر ولوحة تحكم الأدمن -----------------


@dp.message(Command("cleardata"))
@dp.message(Command("reset"))
async def cmd_clear_data(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer(f"⚠️ هذا الأمر متاح للأدمن فقط. معرفك: <code>{message.from_user.id}</code>", parse_mode="HTML")
        return
        
    excel_parser.reset_leagues_data()
    await message.answer("🗑️ <b>تم مسح وتصفير كافة بيانات الحسابات والليجات بنجاح!</b>\n\nأصبح التطبيق وقاعدة البيانات مصفّرة الآن (0 حسابات) وبانتظار رفع ملف إكسل جديد.", parse_mode="HTML")

@dp.callback_query(F.data == "admin_clear_data")
async def cb_admin_clear_data(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    await callback.answer()
    excel_parser.reset_leagues_data()
    await callback.message.answer("🗑️ <b>تم مسح وتصفير كافة بيانات الحسابات والليجات بنجاح يا أبو حمدي!</b>\nالتطبيق الآن نظيف تماماً بانتظار رفع ملف الإكسيل الجديد.", parse_mode="HTML")

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    stats = database.get_dashboard_stats()
    current_data = excel_parser.get_current_leagues_data()
    
    text = (
        f"👑 <b>لوحة تحكم الأدمن - أبو حمدي:</b>\n\n"
        f"👥 إجمالي المستخدمين: <b>{stats['total_users']}</b>\n"
        f"🟢 المشتركين النشطين: <b>{stats['active_users']}</b>\n"
        f"🎟 الأكواد غير المستخدمة: <b>{stats['unused_keys']}</b>\n"
        f"📊 الحسابات الحالية بالتطبيق: <b>{current_data['total_accounts']}</b>\n"
        f"🕒 آخر تحديث للملف: <b>{current_data.get('updated_at') or 'لم يُرفع بعد'}</b>\n\n"
        f"<b>أوامر الأدمن السريعة:</b>\n"
        f"• 📤 <b>تحديث البيانات:</b> أرسل ملف الإكسل (<code>.xlsx</code>) مباشرة في الشات\n"
        f"• ➕ <b>تفعيل اشتراك:</b> <code>/addsub &lt;user_id&gt; &lt;days&gt;</code>\n"
        f"• ❌ <b>إلغاء اشتراك:</b> <code>/delsub &lt;user_id&gt;</code>\n"
        f"• 🎟 <b>توليد أكواد:</b> <code>/gencode &lt;days&gt; [count]</code>\n"
        f"• 📢 <b>إذاعة للكل:</b> <code>/broadcast &lt;رسالتك&gt;</code>\n"
        f"• 📥 <b>تصدير البيانات:</b> <code>/export</code>\n• 🗑️ <b>تصفير البيانات:</b> <code>/cleardata</code>"
    )
    await message.answer(text, parse_mode="HTML")

@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("غير مصرح لك", show_alert=True)
        return
    await callback.answer()
    stats = database.get_dashboard_stats()
    current_data = excel_parser.get_current_leagues_data()
    msg_lines = [
        "👑 <b>لوحة الأدمن السريعة - أبو حمدي:</b>\n",
        f"• المستخدمين: {stats['total_users']}",
        f"• النشطين: {stats['active_users']}",
        f"• الحسابات بالملف: {current_data['total_accounts']}\n",
        "💡 لرفع ملف جديد، فقط اسحب ملف الإكسل وأفلته هنا في المحادثة!"
    ]
    text = "\n".join(msg_lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎟 توليد 5 أكواد (30 يوم)", callback_data="gen_5_30"), InlineKeyboardButton(text="🎟 كود واحد (30 يوم)", callback_data="gen_1_30")],
        [InlineKeyboardButton(text="🎟 كود سنة (365 يوم)", callback_data="gen_1_365")],
        [InlineKeyboardButton(text="🗑️ مسح وتصفير كل البيانات", callback_data="admin_clear_data")]
    ])
    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")

@dp.message(Command("addsub"))
async def cmd_add_sub(message: types.Message):
    if not is_admin(message.from_user.id):
        return
        
    parts = message.text.split()
    if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
        await message.answer("⚠️ الاستخدام الصحيح:\n<code>/addsub &lt;user_id&gt; &lt;days&gt;</code>\nمثال:\n<code>/addsub 123456789 30</code>", parse_mode="HTML")
        return
        
    target_id = int(parts[1])
    days = int(parts[2])
    
    end_date = database.add_subscription_days(target_id, days)
    await message.answer(f"✅ تم تفعيل الاشتراك للمستخدم <code>{target_id}</code> لمدة {days} يوم!\nينتهي في: {end_date}", parse_mode="HTML")
    
    try:
        await bot.send_message(
            target_id,
            f"🎉 <b>تهانينا!</b> تم تفعيل اشتراكك في بوت الليجات لمدة <b>{days} يوم</b> بواسطة الإدارة.\nينتهي في: {end_date}",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(target_id, True)
        )
    except Exception:
        pass

@dp.message(Command("delsub"))
async def cmd_del_sub(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("⚠️ الاستخدام: <code>/delsub &lt;user_id&gt;</code>", parse_mode="HTML")
        return
    target_id = int(parts[1])
    database.remove_subscription(target_id)
    await message.answer(f"🚫 تم إلغاء اشتراك المستخدم <code>{target_id}</code>.", parse_mode="HTML")

def _normalize_num(val_str: str) -> str:
    eastern_to_western = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return val_str.translate(eastern_to_western)

@dp.message(Command("gencode"))
async def cmd_gen_code(message: types.Message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.answer(
            f"⚠️ <b>عذراً يا {message.from_user.first_name}!</b>\n"
            f"خاصية توليد أكواد الاشتراك مخصصة للأدمن فقط.\n\n"
            f"🆔 <b>معرفك الحالي (Telegram ID):</b> <code>{user_id}</code>\n\n"
            f"📌 <b>لتفعيل حسابك كأدمن:</b>\n"
            f"افتح مشروعك في <b>Railway</b> ⬅️ تبويب <b>Variables</b> ⬅️ أضف هذا الرقم <code>{user_id}</code> داخل متغير <code>ADMIN_IDS</code> واحفظ التغييرات.",
            parse_mode="HTML"
        )
        return
        
    raw_text = _normalize_num(message.text or "")
    parts = raw_text.split()
    
    if len(parts) < 2:
        days = 30
        count = 1
    else:
        if not parts[1].isdigit():
            await message.answer(
                "⚠️ <b>طريقة كتابة الأمر:</b>\n"
                "<code>/gencode &lt;عدد الأيام&gt; &lt;عدد الأكواد&gt;</code>\n\n"
                "📌 <b>أمثلة:</b>\n"
                "• <code>/gencode 30 5</code> (لتوليد 5 أكواد مدة كل كود 30 يوم)\n"
                "• <code>/gencode 30</code> (لتوليد كود واحد 30 يوم)\n"
                "• <code>/gencode 365 1</code> (لتوليد كود سنة كاملة)",
                parse_mode="HTML"
            )
            return
        days = int(parts[1])
        count = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1

    count = max(1, min(count, 50))
    days = max(1, days)
    
    codes = [database.generate_license_key(days) for _ in range(count)]
    codes_str = "\n".join(f"• <code>{c}</code>" for c in codes)
    
    await message.answer(
        f"🎟 <b>تم توليد {count} كود اشتراك بنجاح ({days} يوم):</b>\n\n"
        f"{codes_str}\n\n"
        f"💡 <i>المشترك يستطيع نسخ أي كود والضغط على زر (إدخال كود التفعيل) في البوت ليتفعل حسابه فوراً.</i>",
        parse_mode="HTML"
    )

@dp.message(Command("broadcast"))
async def cmd_broadcast(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("⚠️ يرجى كتابة نص الرسالة بعد الأمر:\n<code>/broadcast مرحباً بجميع المشتركين...</code>", parse_mode="HTML")
        return
        
    text = parts[1]
    users = database.list_all_users()
    sent = 0
    
    for u in users:
        try:
            await bot.send_message(u["user_id"], f"📢 <b>إشعار من الإدارة (أبو حمدي):</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except Exception:
            pass
            
    await message.answer(f"📢 تم إرسال الرسالة إلى {sent} مستخدم بنجاح!")

@dp.message(Command("export"))
async def cmd_export(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    file_path = excel_parser.OUTPUT_DATA_FILE
    if os.path.exists(file_path):
        doc = FSInputFile(file_path, filename="leagues_data.json")
        await message.answer_document(doc, caption="📁 ملف بيانات الليجات المحدثة حالياً.")
    else:
        await message.answer("لا توجد بيانات مرفوعة بعد.")

async def start_bot():
    logging.info("Starting Telegram Bot Polling with token...")
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logging.info("Webhook cleaned, starting polling...")
            await dp.start_polling(bot, drop_pending_updates=True)
            break
        except Exception as e:
            logging.error(f"Telegram polling error: {e}, retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    import asyncio
    asyncio.run(start_bot())
