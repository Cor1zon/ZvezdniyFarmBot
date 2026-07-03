import random
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
 
TOKEN = "8820171167:AAGiEb-WodNUyhPTMdbdUGnZ2AZcREIwdr8"
ADMIN_ID = 901473279
 
# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0, ref_count INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, amount INTEGER, date TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS withdraws
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, status TEXT, date TEXT)''')
    conn.commit()
    conn.close()
 
def get_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT balance, ref_count FROM users WHERE id = ?', (user_id,))
    data = c.fetchone()
    conn.close()
    if data:
        return {'balance': data[0], 'ref_count': data[1]}
    else:
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('INSERT INTO users (id, balance) VALUES (?, ?)', (user_id, 0))
        conn.commit()
        conn.close()
        return {'balance': 0, 'ref_count': 0}
 
def update_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()
 
def add_transaction(user_id, type, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO transactions (user_id, type, amount, date) VALUES (?, ?, ?, ?)',
              (user_id, type, amount, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
 
# --- ГЛАВНОЕ МЕНЮ ---
def main_keyboard():
    keyboard = [
        [InlineKeyboardButton("⚽ Футбол", callback_data="game_football"),
         InlineKeyboardButton("🏀 Баскетбол", callback_data="game_basketball")],
        [InlineKeyboardButton("🎳 Боулинг", callback_data="game_bowling"),
         InlineKeyboardButton("🎯 Дартс", callback_data="game_darts")],
        [InlineKeyboardButton("🎲 Классика (1-10)", callback_data="game_classic")],
        [InlineKeyboardButton("💰 Баланс", callback_data="balance"),
         InlineKeyboardButton("💳 Пополнить", callback_data="deposit")],
        [InlineKeyboardButton("💸 Вывод", callback_data="withdraw"),
         InlineKeyboardButton("🔗 Рефералка", callback_data="ref")],
        [InlineKeyboardButton("🏆 Топ", callback_data="top"),
         InlineKeyboardButton("📞 Поддержка", callback_data="support")],
    ]
    if ADMIN_ID:
        keyboard.append([InlineKeyboardButton("👑 Админ-панель", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)
 
# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if context.args and context.args[0].isdigit() and int(context.args[0]) != user_id:
        ref = int(context.args[0])
        get_user(ref)
        update_balance(ref, 10)
        update_balance(user_id, 5)
        add_transaction(ref, 'ref_bonus', 10)
        add_transaction(user_id, 'ref_bonus', 5)
        await update.message.reply_text(f"✅ Рефералка активирована! +5 звёзд тебе, +10 рефереру.")
    await update.message.reply_text(
        f"🌟 Привет! Твой баланс: {user['balance']} звёзд.\nВыбери игру или действие:",
        reply_markup=main_keyboard()
    )
 
# --- ОБРАБОТЧИК КНОПОК ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
 
    # --- БАЛАНС ---
    if data == "balance":
        user = get_user(user_id)
        await query.edit_message_text(f"💰 Твой баланс: {user['balance']} звёзд.", reply_markup=main_keyboard())
 
    # --- ПОПОЛНЕНИЕ ---
    elif data == "deposit":
        keyboard = [
            [InlineKeyboardButton("⭐ 10", callback_data="deposit_10"), InlineKeyboardButton("⭐ 50", callback_data="deposit_50")],
            [InlineKeyboardButton("⭐ 100", callback_data="deposit_100"), InlineKeyboardButton("⭐ 500", callback_data="deposit_500")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")],
        ]
        await query.edit_message_text("💳 Выбери сумму:", reply_markup=InlineKeyboardMarkup(keyboard))
 
    elif data.startswith("deposit_"):
        amount = int(data.split('_')[1])
        update_balance(user_id, amount)
        add_transaction(user_id, 'deposit', amount)
        await query.edit_message_text(f"✅ Пополнено {amount} звёзд!", reply_markup=main_keyboard())
 
    # --- ВЫВОД ---
    elif data == "withdraw":
        await query.edit_message_text("💸 Введи сумму: /withdraw [сумма]", reply_markup=main_keyboard())
 
    # --- РЕФЕРАЛКА ---
    elif data == "ref":
        link = f"https://t.me/ZvezdniyFarmBot?start={user_id}"
        await query.edit_message_text(f"🔗 Твоя ссылка:\n{link}\n\nЗа друга +10 тебе, +5 ему.", reply_markup=main_keyboard())
 
    # --- ТОП ---
    elif data == "top":
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, balance FROM users ORDER BY balance DESC LIMIT 10')
        rows = c.fetchall()
        conn.close()
        text = "🏆 Топ 10:\n"
        for i, (uid, bal) in enumerate(rows, 1):
            text += f"{i}. ID {uid} — {bal}⭐\n"
        await query.edit_message_text(text, reply_markup=main_keyboard())
 
    # --- ПОДДЕРЖКА ---
    elif data == "support":
        await query.edit_message_text("📞 /support [текст]", reply_markup=main_keyboard())
 
    # --- АДМИНКА ---
    elif data == "admin":
        if user_id != ADMIN_ID:
            await query.edit_message_text("⛔ Недоступно.", reply_markup=main_keyboard())
            return
        keyboard = [
            [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Выдать звёзды", callback_data="admin_give")],
            [InlineKeyboardButton("📤 Заявки на вывод", callback_data="admin_withdraws")],
            [InlineKeyboardButton("📜 История", callback_data="admin_history")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")],
        ]
        await query.edit_message_text("👑 Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))
 
    elif data.startswith("admin_"):
        if user_id != ADMIN_ID:
            await query.edit_message_text("⛔ Недоступно.", reply_markup=main_keyboard())
            return
        if data == "admin_stats":
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            users = c.fetchone()[0]
            c.execute('SELECT SUM(balance) FROM users')
            total = c.fetchone()[0] or 0
            conn.close()
            await query.edit_message_text(f"📊 Всего: {users}\nОбщий баланс: {total}⭐", reply_markup=main_keyboard())
        elif data == "admin_give":
            await query.edit_message_text("💡 /give [ID] [сумма]", reply_markup=main_keyboard())
        elif data == "admin_withdraws":
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT id, user_id, amount FROM withdraws WHERE status = "pending"')
            rows = c.fetchall()
            conn.close()
            if not rows:
                await query.edit_message_text("✅ Заявок нет.", reply_markup=main_keyboard())
                return
            text = "📤 Заявки:\n"
            for w_id, uid, amt in rows:
                text += f"ID {w_id} | {uid} | {amt}⭐\n"
            text += "\n/approve [ID] или /reject [ID]"
            await query.edit_message_text(text, reply_markup=main_keyboard())
        elif data == "admin_history":
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute('SELECT user_id, type, amount, date FROM transactions ORDER BY id DESC LIMIT 10')
            rows = c.fetchall()
            conn.close()
            text = "📜 Последние 10:\n"
            for uid, typ, amt, date in rows:
                text += f"{date} | {uid} | {typ} | {amt}⭐\n"
            await query.edit_message_text(text, reply_markup=main_keyboard())
 
    # --- НАЗАД ---
    elif data == "back":
        await query.edit_message_text("🌟 Главное меню:", reply_markup=main_keyboard())
 
    # === ИГРЫ ===
    elif data.startswith("game_"):
        game = data.split('_')[1]
        context.user_data['game'] = game
        keyboard = [
            [InlineKeyboardButton("5⭐", callback_data=f"game_bet_5"),
             InlineKeyboardButton("10⭐", callback_data=f"game_bet_10")],
            [InlineKeyboardButton("25⭐", callback_data=f"game_bet_25"),
             InlineKeyboardButton("50⭐", callback_data=f"game_bet_50")],
            [InlineKeyboardButton("100⭐", callback_data=f"game_bet_100")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back")],
        ]
        emojis = {"football": "⚽", "basketball": "🏀", "bowling": "🎳", "darts": "🎯", "classic": "🎲"}
        await query.edit_message_text(f"{emojis.get(game, '🎮')} Выбери сумму ставки:", reply_markup=InlineKeyboardMarkup(keyboard))
 
    elif data.startswith("game_bet_"):
        amount = int(data.split('_')[2])
        game = context.user_data.get('game', 'classic')
        user = get_user(user_id)
        if user['balance'] < amount:
            await query.edit_message_text("❌ Недостаточно звёзд.", reply_markup=main_keyboard())
            return
 
        # --- ЛОГИКА ИГР ---
        if game == "football":
            result = random.choice(["гол", "мимо"])
            guess = random.choice(["гол", "мимо"])  # Игрок не выбирает, просто удача
            if result == "гол":
                win = amount * 2
                update_balance(user_id, win)
                add_transaction(user_id, 'game_football_win', win)
                await query.edit_message_text(f"⚽ ГОЛ! Ты выиграл {win}⭐!", reply_markup=main_keyboard())
            else:
                update_balance(user_id, -amount)
                add_transaction(user_id, 'game_football_lose', -amount)
                await query.edit_message_text(f"⚽ Мимо! -{amount}⭐", reply_markup=main_keyboard())
 
        elif game == "basketball":
            result = random.choice(["попадание", "промах"])
            if result == "попадание":
                win = amount * 2
                update_balance(user_id, win)
                add_transaction(user_id, 'game_basketball_win', win)
                await query.edit_message_text(f"🏀 ПОПАДАНИЕ! +{win}⭐", reply_markup=main_keyboard())
            else:
                update_balance(user_id, -amount)
                add_transaction(user_id, 'game_basketball_lose', -amount)
                await query.edit_message_text(f"🏀 Промах! -{amount}⭐", reply_markup=main_keyboard())
 
        elif game == "bowling":
            pins = random.randint(1, 10)
            win = amount * 2 if pins >= 8 else 0
            if win:
                update_balance(user_id, win)
                add_transaction(user_id, 'game_bowling_win', win)
                await query.edit_message_text(f"🎳 Сбито {pins} кеглей! +{win}⭐", reply_markup=main_keyboard())
            else:
                update_balance(user_id, -amount)
                add_transaction(user_id, 'game_bowling_lose', -amount)
                await query.edit_message_text(f"🎳 Только {pins} кеглей! -{amount}⭐", reply_markup=main_keyboard())
 
        elif game == "darts":
            sector = random.randint(1, 20)
            if sector >= 15:
                win = amount * 2
                update_balance(user_id, win)
                add_transaction(user_id, 'game_darts_win', win)
                await query.edit_message_text(f"🎯 Сектор {sector}! +{win}⭐", reply_markup=main_keyboard())
            else:
                update_balance(user_id, -amount)
                add_transaction(user_id, 'game_darts_lose', -amount)
                await query.edit_message_text(f"🎯 Сектор {sector}! -{amount}⭐", reply_markup=main_keyboard())
 
        elif game == "classic":
            guess = random.randint(1, 10)
            result = random.randint(1, 10)
            if guess == result:
                win = amount * 2
                update_balance(user_id, win)
                add_transaction(user_id, 'game_classic_win', win)
                await query.edit_message_text(f"🎲 Угадал! Было {result}. +{win}⭐", reply_markup=main_keyboard())
            else:
                update_balance(user_id, -amount)
                add_transaction(user_id, 'game_classic_lose', -amount)
                await query.edit_message_text(f"🎲 Не угадал. Было {result}. -{amount}⭐", reply_markup=main_keyboard())
 
# --- ТЕКСТОВЫЕ КОМАНДЫ ---
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("❌ /withdraw [сумма]", reply_markup=main_keyboard())
        return
    try:
        amount = int(args[0])
        if amount <= 0:
            await update.message.reply_text("❌ >0", reply_markup=main_keyboard())
            return
    except:
        await update.message.reply_text("❌ Пример: /withdraw 10", reply_markup=main_keyboard())
        return
    user = get_user(user_id)
    if user['balance'] < amount:
        await update.message.reply_text("❌ Недостаточно.", reply_markup=main_keyboard())
        return
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO withdraws (user_id, amount, status, date) VALUES (?, ?, ?, ?)',
              (user_id, amount, 'pending', datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    update_balance(user_id, -amount)
    add_transaction(user_id, 'withdraw_pending', -amount)
    await update.message.reply_text(f"✅ Заявка на {amount}⭐ отправлена!", reply_markup=main_keyboard())
 
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("📞 /support [текст]", reply_markup=main_keyboard())
        return
    message = ' '.join(args)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO support (user_id, message, date) VALUES (?, ?, ?)',
              (user_id, message, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Отправлено!", reply_markup=main_keyboard())
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📩 От {user_id}: {message}")
 
async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Недоступно.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ /give [ID] [сумма]")
        return
    try:
        target = int(args[0])
        amount = int(args[1])
    except:
        await update.message.reply_text("❌ Пример: /give 123456789 50")
        return
    update_balance(target, amount)
    add_transaction(target, 'admin_give', amount)
    await update.message.reply_text(f"✅ {target} +{amount}⭐")
 
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Недоступно.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("❌ /approve [ID]")
        return
    w_id = int(args[0])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE withdraws SET status = "approved" WHERE id = ?', (w_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Заявка {w_id} одобрена.")
 
async def reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Недоступно.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("❌ /reject [ID]")
        return
    w_id = int(args[0])
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE withdraws SET status = "rejected" WHERE id = ?', (w_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Заявка {w_id} отклонена.")
 
# --- ЗАПУСК ---
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CommandHandler("give", give))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("Бот запущен...")
    app.run_polling()
 
if __name__ == "__main__":
    main()
