"""
Ilgor Kasbiy Texnikum - So'rovnoma Bot
@Ilgor_kasbiy_texnikum_bot
"""

import logging
import asyncio
import json
import os
from datetime import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup,
    ReplyKeyboardRemove, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, filters
)
from telegram.constants import ParseMode

# ─────────────────────────────────────────────
# SOZLAMALAR
# ─────────────────────────────────────────────
TOKEN = "8782438286:AAG1PHEaJMmnBUxk3-gyUovLW4tGL-iQAzM"
GROUP_CHAT_ID = -1003629667635   # Natijalar yuboriladigan guruh

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# MA'LUMOTLAR
# ─────────────────────────────────────────────
KURSLAR = ["1-kurs", "2-kurs", "3-kurs", "4-kurs"]

GURUHLAR = [
    "10-25 KTD", "11-25 KTD", "12-25 KTD", "13-25 KTD",
    "14-25 AT", "15-25 AT", "16-25 AT", "17-25", "18-25"
]

# O'qituvchi → Fani
OQITUVCHILAR = [
    ("Mavlyanova Malohat",       "Ingliz tili"),
    ("Nurmuhammedova Charos",    "Ingliz tili"),
    ("Abduolimova Umida",        "Ingliz tili"),
    ("To'rayeva Ezoza",          "Ingliz tili"),
    ("G'ulomjonov Olloyor",      "Rus tili"),
    ("Murodov Abduxoliq",        "Rus tili"),
    ("Abduboyev Jamshid",        "Matematika"),
    ("Sulaymonova Dilrabo",      "Tarix"),
    ("Rustamova Kamola",         "Fizika"),
    ("Rashidov Begzod",          "Jismoniy tarbiya"),
    ("Yo'ldoshev Farrux",        "Informatika"),
    ("Habibullayeva Sitora",     "Informatika"),
    ("Shamsiddinov Muxiddin",    "Axborot texnologiyalar asoslari"),
    ("Xo'jabekov Baxrom",        "Algoritm nazariyasi"),
    ("Yuldashev Farrux",         "Axborot xavfsizligi"),
    ("Habibullayeva Sitora",     "WEB dasturlash"),
    ("Xo'jabekov Baxrom",        "Dasturlash asoslari"),
    ("Shamsiddinov Muxiddin",    "Ma'lumotlar bazasi"),
    ("Xo'jabekov Baxrom",        "Dasturlash tillari"),
    ("Nazarova Temur",           "Avtomabillar tuzilishi"),
    ("Axmedov Sardor",           "Avtomabillar tuzilishi"),
    ("Axmedov Sardor",           "Avto dvigatel servis xizmat"),
    ("Nazarova Temur",           "Avtomabil elektr va elektron jixozlari tuzilishi"),
    ("Rustamova Kamola",         "Elektrotexnika va elektronika asoslari"),
    ("Rustamova Kamola",         "Elektr va elektron jixozlarning elementlar bazasi"),
    ("Shokirova Nigora",         "Iqtisodiyot nazariyasi"),
    ("Shokirova Nigora",         "Pul va banklar"),
    ("Bobomurodova Jahongir",    "Arxitekturaviy shaxarsozlik"),
    ("Bobomurodova Jahongir",    "Binolarning interyer ixozlari"),
    ("Bobomurodova Jahongir",    "Arxitektura materialshunoslik"),
    ("Bobomurodova Jahongir",    "Arxitekturaviy qalamtasvir"),
]

# ─────────────────────────────────────────────
# O'QITUVCHILAR BAHOLASH TIZIMI
# ─────────────────────────────────────────────

# Baholash tizimi (ballar)
TUSHUNTIRISH_BALLAR = {
    "tush_1": 4,  # Har doim
    "tush_2": 3,  # Ko'pincha
    "tush_3": 2,  # Kamdan-kam
    "tush_4": 1,  # Umuman tushunarsiz
}

MUNOSABAT_BALLAR = {
    "mun_1": 3,  # Juda yaxshi
    "mun_2": 2,  # O'rtacha
    "mun_3": 1,  # Qo'pol/Adolatsiz
}

# O'qituvchilar statistikasi
OQITUVCHILAR_STATISTIKA = {}

# ─────────────────────────────────────────────
# HOLATLAR (ConversationHandler states)
# ─────────────────────────────────────────────
(
    ASK_NAME,              # Ism va familiya so'rash
    SELECT_KURS,
    SELECT_GURUH,
    TEACHER_START,          # Birinchi savol: "dars o'tadimi?"
    TEACHER_TUSHUNTIRISH,   # Savol 1
    TEACHER_MUNOSABAT,      # Savol 2
    GENERAL_YETISHMAYAPTI,  # Savol 3 (ko'p tanlov)
    GENERAL_BAHO,           # Savol 4
) = range(8)

# ─────────────────────────────────────────────
# YORDAMCHI FUNKSIYALAR
# ─────────────────────────────────────────────

def get_state(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Foydalanuvchi holatini qaytarida."""
    if "survey" not in context.user_data:
        context.user_data["survey"] = {
            "full_name": None,        # Ism va familiya
            "kurs": None,
            "guruh": None,
            "teacher_idx": 0,        # Hozirgi o'qituvchi indeksi
            "teachers_data": [],     # [ {name, fan, dars_bormi, tushuntirish, munosabat} ]
            "yetishmayapti": [],
            "baho": None,
        }
    return context.user_data["survey"]


def current_teacher(context) -> tuple:
    """Hozirgi o'qituvchi (ism, fan)."""
    s = get_state(context)
    idx = s["teacher_idx"]
    if idx < len(OQITUVCHILAR):
        return OQITUVCHILAR[idx]
    return None, None


# ─────────────────────────────────────────────
# O'QITUVCHILAR STATISTIKASI FUNKSIYALARI
# ─────────────────────────────────────────────

def update_teacher_stats(teacher_name: str, teacher_fan: str, dars_bormi: bool, 
                        tushuntirish: str = None, munosabat: str = None):
    """O'qituvchi statistikasini yangilash."""
    key = f"{teacher_name}_{teacher_fan}"
    
    if key not in OQITUVCHILAR_STATISTIKA:
        OQITUVCHILAR_STATISTIKA[key] = {
            "name": teacher_name,
            "fan": teacher_fan,
            "jami_baholar": 0,
            "dars_bor_soni": 0,
            "tushuntirish_ballari": [],
            "munosabat_ballari": [],
            "umumiy_ball": 0,
            "baholangan_soni": 0
        }
    
    stats = OQITUVCHILAR_STATISTIKA[key]
    stats["jami_baholar"] += 1
    
    if dars_bormi:
        stats["dars_bor_soni"] += 1
        
        if tushuntirish:
            tush_ball = TUSHUNTIRISH_BALLAR.get(tushuntirish, 0)
            stats["tushuntirish_ballari"].append(tush_ball)
            
        if munosabat:
            mun_ball = MUNOSABAT_BALLAR.get(munosabat, 0)
            stats["munosabat_ballari"].append(mun_ball)
            
        # Umumiy ballni hisoblash
        tush_orta = sum(stats["tushuntirish_ballari"]) / len(stats["tushuntirish_ballari"]) if stats["tushuntirish_ballari"] else 0
        mun_orta = sum(stats["munosabat_ballari"]) / len(stats["munosabat_ballari"]) if stats["munosabat_ballari"] else 0
        stats["umumiy_ball"] = round((tush_orta + mun_orta) / 2, 2)
        stats["baholangan_soni"] = len(stats["tushuntirish_ballari"])


def get_teacher_rating(teacher_name: str, teacher_fan: str) -> dict:
    """O'qituvchi reytingini olish."""
    key = f"{teacher_name}_{teacher_fan}"
    return OQITUVCHILAR_STATISTIKA.get(key, None)


def get_top_teachers(limit: int = 5) -> list:
    """Eng yaxshi o'qituvchilar ro'yxati."""
    teachers_with_rating = []
    
    for key, stats in OQITUVCHILAR_STATISTIKA.items():
        if stats["baholangan_soni"] > 0:  # Kamida 1 marta baholangan bo'lishi kerak
            teachers_with_rating.append(stats)
    
    # Umumiy ball bo'yicha saralash
    teachers_with_rating.sort(key=lambda x: x["umumiy_ball"], reverse=True)
    return teachers_with_rating[:limit]


# ─────────────────────────────────────────────
# FAYLGA SAQLASH FUNKSIYALARI
# ─────────────────────────────────────────────

DATA_FILE = "survey_data.json"

def save_survey_to_file(survey_data: dict, user_info: dict):
    """So'rovnomani faylga saqlaydi."""
    try:
        # Avvalgi ma'lumotlarni yuklash
        existing_data = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
        
        # Yangi so'rovnomani qo'shish
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "user_info": {
                "full_name": survey_data['full_name'],
                "telegram_username": user_info.get('username', 'nomalum'),
                "telegram_id": user_info.get('id', 0),
                "kurs": survey_data['kurs'],
                "guruh": survey_data['guruh']
            },
            "teachers_data": survey_data['teachers_data'],
            "yetishmayapti": survey_data['yetishmayapti'],
            "baho": survey_data['baho']
        }
        
        existing_data.append(new_entry)
        
        # Faylga saqlash
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"So'rovnomani faylga saqlandi: {survey_data['full_name']}")
        return True
        
    except Exception as e:
        logger.error(f"So'rovnomani faylga saqlashda xato: {e}")
        return False


def save_statistics_to_file():
    """Statistikani faylga saqlaydi."""
    try:
        stats_file = "statistics.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(OQITUVCHILAR_STATISTIKA, f, ensure_ascii=False, indent=2)
        logger.info("Statistika faylga saqlandi")
        return True
    except Exception as e:
        logger.error(f"Statistikani faylga saqlashda xato: {e}")
        return False


def load_statistics_from_file():
    """Statistikani fayldan yuklaydi."""
    try:
        stats_file = "statistics.json"
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                loaded_stats = json.load(f)
                OQITUVCHILAR_STATISTIKA.clear()
                OQITUVCHILAR_STATISTIKA.update(loaded_stats)
            logger.info("Statistika fayldan yuklandi")
            return True
    except Exception as e:
        logger.error(f"Statistikani fayldan yuklashda xato: {e}")
    return False


def teachers_inline(teacher_name: str, fan: str) -> InlineKeyboardMarkup:
    """'Sizga ... dars o'tadimi?' uchun tugmalar."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ha", callback_data="dars_ha"),
        InlineKeyboardButton("❌ Yo'q", callback_data="dars_yoq"),
    ]])


def tushuntirish_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🟢 Har doim",        callback_data="tush_1"),
        InlineKeyboardButton("🟡 Ko'pincha",       callback_data="tush_2"),
    ], [
        InlineKeyboardButton("🔴 Kamdan-kam",      callback_data="tush_3"),
        InlineKeyboardButton("⚪️ Umuman tushunarsiz", callback_data="tush_4"),
    ]])


def munosabat_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("👍 Juda yaxshi",     callback_data="mun_1"),
        InlineKeyboardButton("😐 O'rtacha",        callback_data="mun_2"),
        InlineKeyboardButton("👎 Qo'pol/Adolatsiz",callback_data="mun_3"),
    ]])


def yetishmayapti_inline(selected: list) -> InlineKeyboardMarkup:
    """Ko'p tanlov - belgilangan variantlar ✅ belgisi bilan."""
    options = [
        ("💻 Kompyuter / Texnika",    "yet_1"),
        ("🧪 Amaliy mashg'ulotlar",   "yet_2"),
        ("📚 Yangi darsliklar",        "yet_3"),
        ("🌐 Internet / Wi-Fi",        "yet_4"),
        ("🔥 Isitish / Sharoit",       "yet_5"),
    ]
    buttons = []
    for label, cb in options:
        prefix = "✅ " if cb in selected else ""
        buttons.append([InlineKeyboardButton(f"{prefix}{label}", callback_data=cb)])
    buttons.append([InlineKeyboardButton("➡️ Davom etish", callback_data="yet_done")])
    return InlineKeyboardMarkup(buttons)


def baho_inline() -> InlineKeyboardMarkup:
    row1 = [InlineKeyboardButton(str(i), callback_data=f"baho_{i}") for i in range(1, 6)]
    row2 = [InlineKeyboardButton(str(i), callback_data=f"baho_{i}") for i in range(6, 11)]
    return InlineKeyboardMarkup([row1, row2])


# ─────────────────────────────────────────────
# NATIJA FORMATLASH VA YUBORISH
# ─────────────────────────────────────────────

TUSHUNTIRISH_LABELS = {
    "tush_1": "🟢 Har doim",
    "tush_2": "🟡 Ko'pincha",
    "tush_3": "🔴 Kamdan-kam",
    "tush_4": "⚪️ Umuman tushunarsiz",
}

MUNOSABAT_LABELS = {
    "mun_1": "👍 Juda yaxshi",
    "mun_2": "😐 O'rtacha",
    "mun_3": "👎 Qo'pol / Adolatsiz",
}

YETISHMAYAPTI_LABELS = {
    "yet_1": "💻 Kompyuter / Texnika",
    "yet_2": "🧪 Amaliy mashg'ulotlar",
    "yet_3": "📚 Yangi darsliklar",
    "yet_4": "🌐 Internet / Wi-Fi",
    "yet_5": "🔥 Isitish / Sharoit",
}


async def send_results(context: ContextTypes.DEFAULT_TYPE, user: object, s: dict):
    """Natijalarni guruhga yuboradi va statistikani yangilaydi."""
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    
    # Avval statistikani yangilaymiz
    for td in s["teachers_data"]:
        update_teacher_stats(
            td["name"], 
            td["fan"], 
            td["dars_bormi"],
            td.get("tushuntirish"),
            td.get("munosabat")
        )
    
    # So'rovnomani faylga saqlaymiz
    save_survey_to_file(s, {
        'username': user.username,
        'id': user.id
    })
    
    # Statistikani ham faylga saqlaymiz
    save_statistics_to_file()
    
    lines = [
        "📋 *YANGI SO'ROVNOMA NATIJASI*",
        f"🏫 Ilgor Kasbiy Mahorat Texnikumi",
        f"📅 Sana: {now}",
        f"👤 Talaba: *{s['full_name']}*",
        f"📱 Telegram: @{user.username or 'nomalum'} (ID: {user.id})",
        f"📚 Kurs: {s['kurs']}  |  Guruh: {s['guruh']}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "👨‍🏫 *O'QITUVCHILAR BAHOLARI:*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    for td in s["teachers_data"]:
        lines.append(f"\n🔹 *{td['name']}* — _{td['fan']}_")
        if not td["dars_bormi"]:
            lines.append("   ↳ Dars o'tmaydi (o'tkazib yuborildi)")
        else:
            tush = TUSHUNTIRISH_LABELS.get(td.get("tushuntirish", ""), "—")
            mun  = MUNOSABAT_LABELS.get(td.get("munosabat", ""), "—")
            lines.append(f"   📖 Tushuntirish: {tush}")
            lines.append(f"   🤝 Munosabat: {mun}")
            
            # Joriy bahoni ko'rsatish
            tush_ball = TUSHUNTIRISH_BALLAR.get(td.get("tushuntirish", ""), 0)
            mun_ball = MUNOSABAT_BALLAR.get(td.get("munosabat", ""), 0)
            joriy_ball = round((tush_ball + mun_ball) / 2, 1)
            lines.append(f"   ⭐ Joriy baho: {joriy_ball}/3.5")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "🏫 *TEXNIKUM BAHOLARI:*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if s["yetishmayapti"]:
        yet_labels = [YETISHMAYAPTI_LABELS.get(k, k) for k in s["yetishmayapti"]]
        lines.append("❗ Yetishmayotgan narsalar:")
        for lbl in yet_labels:
            lines.append(f"   • {lbl}")
    else:
        lines.append("❗ Yetishmayotgan narsalar: belgilanmagan")

    lines.append(f"⭐ Ta'lim sifati bahosi: *{s['baho']} / 10*")

    text = "\n".join(lines)

    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Guruhga yuborishda xato: {e}")


# ─────────────────────────────────────────────
# HANDLERS
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Botga kirish. /start buyrug'i."""
    context.user_data.clear()   # Eski holatni tozalash
    keyboard = [[KeyboardButton("📝 So'rovnomani boshlash")]]
    await update.message.reply_text(
        "🏫 *Ilgor Kasbiy Mahorat Texnikumi*\n\n"
        "Assalomu alaykum! 👋\n\n"
        "Bu bot orqali siz texnikum va o'qituvchilarimiz haqida "
        "anonim baholash o'tkazishingiz mumkin.\n\n"
        "So'rovnomani boshlash uchun quyidagi tugmani bosing 👇",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )


async def begin_survey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """So'rovnomani boshlash → Ism va familiya so'rash."""
    get_state(context)  # holatni initsializatsiya qilish
    await update.message.reply_text(
        "📝 *So'rovnomaga xush kelibsiz!*\n\n"
        "Iltimos, to'liq ismingiz va familiyangizni kiriting:\n"
        "_(Masalan: Aliyev Valijon)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ism va familiyani saqlash → Kurs tanlash."""
    full_name = update.message.text.strip()
    
    # Minimal tekshiruv - kamida 2 so'z bo'lishi kerak
    if len(full_name.split()) < 2:
        await update.message.reply_text(
            "❌ Iltimos, to'liq ism va familiyangizni kiriting:\n"
            "_(Masalan: Aliyev Valijon)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return ASK_NAME
    
    s = get_state(context)
    s["full_name"] = full_name
    
    buttons = [[InlineKeyboardButton(k, callback_data=f"kurs_{k}")] for k in KURSLAR]
    await update.message.reply_text(
        f"✅ Ism: *{full_name}*\n\n"
        "📚 *Qaysi kursdа o'qiysiz?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return SELECT_KURS


async def select_kurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kurs tanlandi → Guruh tanlash."""
    query = update.callback_query
    await query.answer()
    kurs = query.data.replace("kurs_", "")
    s = get_state(context)
    s["kurs"] = kurs

    buttons = [[InlineKeyboardButton(g, callback_data=f"guruh_{g}")] for g in GURUHLAR]
    await query.edit_message_text(
        f"✅ Kurs: *{kurs}*\n\n🏫 Endi guruhingizni tanlang:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return SELECT_GURUH


async def select_guruh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guruh tanlandi → O'qituvchilar bloki boshlanadi."""
    query = update.callback_query
    await query.answer()
    guruh = query.data.replace("guruh_", "")
    s = get_state(context)
    s["guruh"] = guruh
    s["teacher_idx"] = 0

    await query.edit_message_text(
        f"✅ Kurs: *{s['kurs']}* | Guruh: *{guruh}*\n\n"
        "📋 Endi o'qituvchilaringizni baholashni boshlaymiz.\n\n"
        "‼️ So'rovnoma anonim. Hech kim siz kim ekanligingizni bilmaydi.",
        parse_mode=ParseMode.MARKDOWN,
    )
    return await ask_teacher_dars(update, context, query.message.chat_id)


async def ask_teacher_dars(update, context, chat_id=None):
    """Hozirgi o'qituvchi uchun 'Dars o'tadimi?' savoli."""
    s = get_state(context)
    name, fan = current_teacher(context)

    if name is None:
        # Barcha o'qituvchilar tugadi
        return await ask_general(update, context, chat_id)

    if chat_id is None:
        chat_id = update.effective_chat.id

    text = (
        f"👨‍🏫 *{name}*\n"
        f"📖 Fan: _{fan}_\n\n"
        f"Sizga bu o'qituvchi dars o'tadimi?"
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=teachers_inline(name, fan),
    )
    return TEACHER_START


async def teacher_dars_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """'Dars o'tadimi?' javobini qayta ishlash."""
    query = update.callback_query
    await query.answer()
    s = get_state(context)
    name, fan = current_teacher(context)

    if query.data == "dars_yoq":
        # O'tkazib yuboriladi
        s["teachers_data"].append({"name": name, "fan": fan, "dars_bormi": False})
        s["teacher_idx"] += 1
        await query.edit_message_text(
            f"⏭ *{name}* — o'tkazib yuborildi.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return await ask_teacher_dars(update, context, query.message.chat_id)

    # Ha → Savol 1
    s["teachers_data"].append({"name": name, "fan": fan, "dars_bormi": True})
    await query.edit_message_text(
        f"👨‍🏫 *{name}* — _{fan}_\n\n"
        f"1️⃣ O'qituvchi mavzuni *tushunarli tushuntiradimi?*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=tushuntirish_inline(),
    )
    return TEACHER_TUSHUNTIRISH


async def teacher_tushuntirish_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tushuntirish bahosini saqlash → Munosabat savoli."""
    query = update.callback_query
    await query.answer()
    s = get_state(context)
    s["teachers_data"][-1]["tushuntirish"] = query.data
    name, fan = current_teacher(context)

    tush_label = TUSHUNTIRISH_LABELS.get(query.data, "")
    await query.edit_message_text(
        f"👨‍🏫 *{name}* — _{fan}_\n\n"
        f"✅ Tushuntirish: {tush_label}\n\n"
        f"2️⃣ Ustozning talabalarga nisbatan *munosabati (etikasi)* qanday?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=munosabat_inline(),
    )
    return TEACHER_MUNOSABAT


async def teacher_munosabat_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Munosabat bahosini saqlash → Keyingi o'qituvchi."""
    query = update.callback_query
    await query.answer()
    s = get_state(context)
    s["teachers_data"][-1]["munosabat"] = query.data
    name, fan = current_teacher(context)

    mun_label = MUNOSABAT_LABELS.get(query.data, "")
    await query.edit_message_text(
        f"✅ *{name}* baholandi!\n"
        f"   📖 Tushuntirish: {TUSHUNTIRISH_LABELS.get(s['teachers_data'][-1]['tushuntirish'], '')}\n"
        f"   🤝 Munosabat: {mun_label}",
        parse_mode=ParseMode.MARKDOWN,
    )
    s["teacher_idx"] += 1
    return await ask_teacher_dars(update, context, query.message.chat_id)


# ─────────────────────────────────────────────
# UMUMIY SAVOLLAR
# ─────────────────────────────────────────────

async def ask_general(update, context, chat_id=None):
    """O'qituvchilar tugagach — texnikum savollari."""
    s = get_state(context)
    s["yetishmayapti"] = []
    if chat_id is None:
        chat_id = update.effective_chat.id

    await context.bot.send_message(
        chat_id=chat_id,
        text=(
            "🎉 Barcha o'qituvchilar baholandi!\n\n"
            "Endi texnikum sharoiti haqida bir necha savol.\n\n"
            "3️⃣ *Sizningcha, darslarda nima yetishmayapti?*\n"
            "_(Bir nechta variant tanlashingiz mumkin, tugamgandan so'ng "
            "\"Davom etish\" tugmasini bosing)_"
        ),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=yetishmayapti_inline([]),
    )
    return GENERAL_YETISHMAYAPTI


async def general_yetishmayapti_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ko'p tanlov ishlash."""
    query = update.callback_query
    await query.answer()
    s = get_state(context)

    if query.data == "yet_done":
        # Keyingi savol
        await query.edit_message_text(
            "4️⃣ *Texnikumdagi ta'lim sifatini 1 dan 10 gacha baholang:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=baho_inline(),
        )
        return GENERAL_BAHO

    # Toggle tanlash
    selected = s["yetishmayapti"]
    if query.data in selected:
        selected.remove(query.data)
    else:
        selected.append(query.data)

    await query.edit_message_reply_markup(
        reply_markup=yetishmayapti_inline(selected),
    )
    return GENERAL_YETISHMAYAPTI


async def general_baho_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Baho saqlash → So'rovnomani tugatish."""
    query = update.callback_query
    await query.answer()
    s = get_state(context)
    baho = int(query.data.replace("baho_", ""))
    s["baho"] = baho

    stars = "⭐" * baho
    await query.edit_message_text(
        f"✅ Ta'lim sifati bahosi: *{baho}/10* {stars}\n\n"
        "✅ *So'rovnoma yakunlandi!*\n\n"
        "Javoblaringiz uchun katta rahmat! 🙏\n"
        "Sizning javoblaringiz texnikum sifatini yaxshilashga xizmat qiladi.\n\n"
        "Yana boshqatdan o'tkazish uchun /start buyrug'ini bosing.",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Guruhga yuborish
    await send_results(context, update.effective_user, s)
    return ConversationHandler.END




async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ So'rovnoma bekor qilindi.\n\nQayta boshlash uchun /start bosing.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ─────────────────────────────────────────────
# STATISTIKA KOMANDALARI
# ─────────────────────────────────────────────

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Umumiy statistikani ko'rsatish."""
    if not OQITUVCHILAR_STATISTIKA:
        await update.message.reply_text(
            "📊 *STATISTIKA*\n\nHozircha ma'lumotlar yo'q.\n"
            "So'rovnomalar to'plangach statistika paydo bo'ladi.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    lines = [
        "📊 *O'QITUVCHILAR STATISTIKASI*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    
    # Faqat baholangan o'qituvchilar
    baholangan_ustozlar = []
    for key, stats in OQITUVCHILAR_STATISTIKA.items():
        if stats["baholangan_soni"] > 0:
            baholangan_ustozlar.append(stats)
    
    if not baholangan_ustozlar:
        lines.append("Hozircha baholangan o'qituvchilar yo'q.")
    else:
        # Saralash (eng yuqori ball birinchi)
        baholangan_ustozlar.sort(key=lambda x: x["umumiy_ball"], reverse=True)
        
        for i, stats in enumerate(baholangan_ustozlar, 1):
            foiz = round((stats["dars_bor_soni"] / stats["jami_baholar"]) * 100) if stats["jami_baholar"] > 0 else 0
            lines.append(f"{i}. *{stats['name']}* — _{stats['fan']}_")
            lines.append(f"   ⭐ Reyting: {stats['umumiy_ball']}/3.5")
            lines.append(f"   📈 Baholar: {stats['baholangan_soni']} marta")
            lines.append(f"   ✅ Dars o'tish: {foiz}%")
            lines.append("")
    
    text = "\n".join(lines)
    
    try:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Statistikani yuborishda xato: {e}")


async def show_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Eng yaxshi 5 o'qituvchini ko'rsatish."""
    top_teachers = get_top_teachers(5)
    
    if not top_teachers:
        await update.message.reply_text(
            "🏆 *TOP O'QITUVCHILAR*\n\n"
            "Hozircha ma'lumotlar yo'q.\n"
            "So'rovnomalar to'plangac reyting shakllanadi.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    lines = [
        "🏆 *ENG YAXSHI 5 O'QITUVCHI*",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]
    
    for i, stats in enumerate(top_teachers, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        lines.append(f"{medal} *{stats['name']}* — _{stats['fan']}_")
        lines.append(f"   ⭐ Reyting: {stats['umumiy_ball']}/3.5")
        lines.append(f"   📈 Baholar: {stats['baholangan_soni']} marta")
        
        # Qo'shimcha ma'lumot
        if stats["tushuntirish_ballari"]:
            tush_orta = round(sum(stats["tushuntirish_ballari"]) / len(stats["tushuntirish_ballari"]), 1)
            lines.append(f"   📖 Tushuntirish: {tush_orta}/4")
        
        if stats["munosabat_ballari"]:
            mun_orta = round(sum(stats["munosabat_ballari"]) / len(stats["munosabat_ballari"]), 1)
            lines.append(f"   🤝 Munosabat: {mun_orta}/3")
        
        lines.append("")
    
    text = "\n".join(lines)
    
    try:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        logger.error(f"Top reytingini yuborishda xato: {e}")


# ─────────────────────────────────────────────
# BOTNI YOQISH
# ─────────────────────────────────────────────

def main():
    # Avvalgi statistikani fayldan yuklash
    load_statistics_from_file()
    
    app = Application.builder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📝 So'rovnomani boshlash$"), begin_survey),
            CommandHandler("start", start),
        ],
        states={
            ASK_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name),
            ],
            SELECT_KURS: [CallbackQueryHandler(select_kurs, pattern=r"^kurs_")],
            SELECT_GURUH: [CallbackQueryHandler(select_guruh, pattern=r"^guruh_")],
            TEACHER_START: [
                CallbackQueryHandler(teacher_dars_callback, pattern=r"^dars_"),
            ],
            TEACHER_TUSHUNTIRISH: [
                CallbackQueryHandler(teacher_tushuntirish_callback, pattern=r"^tush_"),
            ],
            TEACHER_MUNOSABAT: [
                CallbackQueryHandler(teacher_munosabat_callback, pattern=r"^mun_"),
            ],
            GENERAL_YETISHMAYAPTI: [
                CallbackQueryHandler(general_yetishmayapti_callback, pattern=r"^(yet_|yet_done)"),
            ],
            GENERAL_BAHO: [
                CallbackQueryHandler(general_baho_callback, pattern=r"^baho_"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CommandHandler("stat", show_stats))
    app.add_handler(CommandHandler("top", show_top))

    logger.info("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
