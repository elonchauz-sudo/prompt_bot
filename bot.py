import asyncio
import logging
import html
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ⚙️ SOZLAMALAR
API_TOKEN = "8958977800:AAHZjEL3O5Am7OSbVek84rYEkgrSV2oSgmY"
ADMIN_ID = 5874144878  # O'zingizning Telegram ID raqamingiz
CHANNEL_USERNAME = "@prompt_k"  # Majburiy obuna kanali

router = Router()
bot = Bot(token=API_TOKEN)

# 📌 BAZALAR VA SOZLAMALAR
PROMPTS_DB = {
    "1": "Sen professional copywriter san. Menga Instagram uchun 7 kunlik kontent reja tuzib ber.",
    "534": "Sen tajribali Python dasturchisan. Menga aiogram 3 da to'lov bot kodi yozib ber.",
}
USERS_SET = set()

PAYMENT_SETTINGS = {
    "card": "8600 1234 5678 9012",
    "amount": "5,000 so'm"
}


# 🔄 FSM (Holatlar)
class PaymentState(StatesGroup):
    waiting_for_receipt = State()

class AdminState(StatesGroup):
    waiting_for_prompt_id = State()
    waiting_for_prompt_text = State()
    waiting_for_delete_id = State()
    waiting_for_new_card = State()
    waiting_for_new_amount = State()
    waiting_for_broadcast = State()


# --- OBUNANI TEKSHIRISH ---
async def check_subscription(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception:
        pass
    return False


# ==================== ADMIN PANEL QISMI ====================

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Prompt qo'shish", callback_data="admin_add")
    builder.button(text="🗑 Promptni o'chirish", callback_data="admin_del")
    builder.button(text="📋 Promptlar ro'yxati", callback_data="admin_list")
    builder.button(text="💳 Kartani tahrirlash", callback_data="admin_edit_card")
    builder.button(text="💰 Summani o'zgartirish", callback_data="admin_edit_amount")
    builder.button(text="📢 Xabar tarqatish", callback_data="admin_broadcast")
    builder.button(text="📊 Statistika", callback_data="admin_stats")
    builder.adjust(2)

    await message.answer(
        "🛠 <b>Admin boshqaruv paneli:</b>\nKerakli amalni tanlang:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    text = (
        f"📊 <b>Bot statistikasi:</b>\n\n"
        f"👥 Jami foydalanuvchilar: {len(USERS_SET)} ta\n"
        f"📝 Jami promptlar: {len(PROMPTS_DB)} ta\n"
        f"💳 Joriy karta: <code>{PAYMENT_SETTINGS['card']}</code>\n"
        f"💰 Joriy summa: <b>{PAYMENT_SETTINGS['amount']}</b>"
    )
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "admin_list")
async def show_prompts_list(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    if not PROMPTS_DB:
        await callback.message.edit_text("Hozircha baza bo'sh.")
        await callback.answer()
        return

    text = "📋 <b>Mavjud promptlar:</b>\n\n"
    for p_id, p_text in PROMPTS_DB.items():
        text += f"🔹 <b>#{p_id}</b>: {html.escape(p_text[:40])}...\n"

    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer()


# 1-QADAM: Prompt qo'shish (Kodni so'rash)
@router.callback_query(F.data == "admin_add")
async def start_add_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("1️⃣ Yangi prompt uchun <b>kodni (raqamni)</b> kiriting (masalan: <code>101</code>):", parse_mode="HTML")
    await state.set_state(AdminState.waiting_for_prompt_id)
    await callback.answer()

@router.message(AdminState.waiting_for_prompt_id)
async def process_new_prompt_id(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    await state.update_data(new_id=message.text)
    # 2-QADAM: Prompt matnini so'rash
    await message.answer(f"2️⃣ Endi <b>#{message.text}</b> kodi uchun <b>prompt matnini</b> yuboring:", parse_mode="HTML")
    await state.set_state(AdminState.waiting_for_prompt_text)

@router.message(AdminState.waiting_for_prompt_text)
async def process_new_prompt_text(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    data = await state.get_data()
    prompt_id = data.get("new_id")
    
    PROMPTS_DB[prompt_id] = message.text
    await message.answer(f"✅ Muvaffaqiyatli saqlandi! Kod: <b>#{prompt_id}</b>", parse_mode="HTML")
    await state.clear()


# Promptni o'chirish
@router.callback_query(F.data == "admin_del")
async def start_del_prompt(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("O'chirmoqchi bo'lgan prompt kodini yuboring (masalan: <code>534</code>):", parse_mode="HTML")
    await state.set_state(AdminState.waiting_for_delete_id)
    await callback.answer()

@router.message(AdminState.waiting_for_delete_id)
async def process_delete_prompt(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    prompt_id = message.text
    if prompt_id in PROMPTS_DB:
        del PROMPTS_DB[prompt_id]
        await message.answer(f"🗑 <b>#{prompt_id}</b> raqamli prompt o'chirildi!", parse_mode="HTML")
    else:
        await message.answer("❌ Bunday kodli prompt topilmadi.")
    await state.clear()


# Kartani tahrirlash
@router.callback_query(F.data == "admin_edit_card")
async def edit_card_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer(f"Hozirgi karta: <code>{PAYMENT_SETTINGS['card']}</code>\nYangi karta raqamini yuboring:", parse_mode="HTML")
    await state.set_state(AdminState.waiting_for_new_card)
    await callback.answer()

@router.message(AdminState.waiting_for_new_card)
async def save_new_card(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    PAYMENT_SETTINGS["card"] = message.text
    await message.answer(f"✅ Karta raqami o'zgartirildi: <code>{message.text}</code>", parse_mode="HTML")
    await state.clear()


# Summani o'zgartirish
@router.callback_query(F.data == "admin_edit_amount")
async def edit_amount_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer(f"Hozirgi summa: {PAYMENT_SETTINGS['amount']}\nYangi summani yuboring:")
    await state.set_state(AdminState.waiting_for_new_amount)
    await callback.answer()

@router.message(AdminState.waiting_for_new_amount)
async def save_new_amount(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    PAYMENT_SETTINGS["amount"] = message.text
    await message.answer(f"✅ Summa o'zgartirildi: <b>{message.text}</b>", parse_mode="HTML")
    await state.clear()


# Foydalanuvchilarga xabar tarqatish (Rassilka)
@router.callback_query(F.data == "admin_broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring (matn, rasm yoki video):")
    await state.set_state(AdminState.waiting_for_broadcast)
    await callback.answer()

@router.message(AdminState.waiting_for_broadcast)
async def send_broadcast(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID: return
    
    success = 0
    failed = 0
    await message.answer("⏳ Xabar tarqatish boshlandi...")
    
    for user_id in USERS_SET:
        try:
            await message.copy_to(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1
            
    await message.answer(f"✅ Xabar tarqatib bo'lindi!\n\nYetib bordi: {success} ta\nYetib bormadi: {failed} ta")
    await state.clear()


# ==================== FOYDALANUVCHI QISMI ====================

@router.message(Command("start"))
async def start_cmd(message: Message):
    user_id = message.from_user.id
    USERS_SET.add(user_id)

    is_subscribed = await check_subscription(user_id)
    if not is_subscribed:
        builder = InlineKeyboardBuilder()
        builder.button(text="📢 Kanalga obuna bo'lish", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")
        builder.button(text="🔄 Tekshirish", callback_data="check_sub")
        builder.adjust(1)
        
        await message.answer(
            "⚠️ Botdan to‘liq foydalanish uchun avval quyidagi kanalimizga obuna bo‘ling va 'Tekshirish' tugmasini bosing:",
            reply_markup=builder.as_markup()
        )
        return

    name = html.escape(message.from_user.first_name)
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"
    
    await message.answer(
        f"👋🏻 Assalomu alaykum, {mention}!\n\n"
        f"O‘zingizga kerakli bo‘lgan <b>prompt kodini</b> yuboring (masalan: <code>1</code> yoki <code>534</code>).",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "check_sub")
async def verify_subscription(callback: CallbackQuery):
    user_id = callback.from_user.id
    if not await check_subscription(user_id):
        await callback.answer("❌ Siz hali kanalga obuna bo'lmadingiz!", show_alert=True)
        return

    await callback.message.delete()
    name = html.escape(callback.from_user.first_name)
    mention = f"<a href='tg://user?id={user_id}'>{name}</a>"
    
    await callback.message.answer(
        f"✅ Obuna tasdiqlandi!\n\n"
        f"👋🏻 Assalomu alaykum, {mention}!\n\n"
        f"O‘zingizga kerakli bo‘lgan <b>prompt kodini</b> yuboring (masalan: <code>1</code> yoki <code>534</code>).",
        parse_mode="HTML"
    )


@router.message(F.text.regexp(r"^\d+$"))
async def ask_for_payment(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if not await check_subscription(user_id):
        await message.answer("⚠️ Botdan foydalanish uchun avval /start buyrug'ini bosing va kanalga obuna bo'ling.")
        return

    prompt_id = message.text
    USERS_SET.add(user_id)

    if prompt_id not in PROMPTS_DB:
        await message.answer("❌ Bunday raqamli prompt topilmadi. Iltimos, mavjud raqamni kiriting.")
        return

    await state.update_data(prompt_id=prompt_id)

    card = PAYMENT_SETTINGS["card"]
    amount = PAYMENT_SETTINGS["amount"]

    text = (
        f"🎯 Siz tanlagan prompt raqami: <b>#{prompt_id}</b>\n\n"
        f"💳 To‘lov uchun karta: <code>{card}</code>\n"
        f"💰 Summa: <b>{amount}</b>\n\n"
        f"Iltimos, ko‘rsatilgan miqdorda to‘lovni amalga oshirgach, <b>to‘lov cheki (skrinshot)ni</b> shu yerga yuboring."
    )

    await message.answer(text, parse_mode="HTML")
    await state.set_state(PaymentState.waiting_for_receipt)


@router.message(PaymentState.waiting_for_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    user_data = await state.get_data()
    prompt_id = user_data.get("prompt_id")

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Tasdiqlash", callback_data=f"approve_{message.from_user.id}_{prompt_id}")
    builder.button(text="❌ Rad etish", callback_data=f"reject_{message.from_user.id}")
    builder.adjust(2)

    username = html.escape(f"@{message.from_user.username}") if message.from_user.username else "Username yo'q"
    admin_text = (
        f"🔔 <b>Yangi to‘lov (Yarim avtomat)!</b>\n\n"
        f"👤 Foydalanuvchi: {username} (<code>{message.from_user.id}</code>)\n"
        f"📌 So‘ralgan prompt: <b>#{prompt_id}</b>"
    )

    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file_id,
        caption=admin_text,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )

    await message.answer("⏳ Chekingiz adminga yuborildi. Tekshirilgach, bot sizga promptni yuboradi.")
    await state.clear()


# ==================== TO'LOVNI TASDIQLASH / RAD ETISH ====================

@router.callback_query(F.data.startswith("approve_"))
async def approve_payment(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data_parts = callback.data.split("_")
    user_id = int(data_parts[1])
    prompt_id = data_parts[2]

    prompt_text = PROMPTS_DB.get(prompt_id, "Kechirasiz, prompt matni topilmadi.")

    # 1. Promptni HTML kod blokida yuborish
    await bot.send_message(
        chat_id=user_id,
        text=f"✅ To‘lovingiz tasdiqlandi! Mana siz so'ragan prompt:\n\n<pre>{html.escape(prompt_text)}</pre>",
        parse_mode="HTML",
    )

    # 2. Qo'shimcha xabar
    await bot.send_message(
        chat_id=user_id,
        text="🎉 Prompt muvaffaqiyatli olindi! Boshqa prompt kodini yuborishda davom etishingiz mumkin.",
    )

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n✅ <b>Holat: Tasdiqlandi</b>", parse_mode="HTML")
    await callback.answer("Muvaffaqiyatli tasdiqlandi!")


@router.callback_query(F.data.startswith("reject_"))
async def reject_payment(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data_parts = callback.data.split("_")
    user_id = int(data_parts[1])

    await bot.send_message(
        chat_id=user_id,
        text="❌ Afsuski, to‘lovingiz rad etildi. Ma'lumotlarni tekshirib qaytadan urinib ko'ring.",
    )

    await callback.message.edit_caption(caption=f"{callback.message.caption}\n\n❌ <b>Holat: Rad etildi</b>", parse_mode="HTML")
    await callback.answer("To'lov rad etildi.")


async def main():
    dp = Dispatcher()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
