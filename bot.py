import random
import sqlite3
import json
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes
 
TOKEN = "8820171167:AAGiEb-WodNUyhPTMdbdUGnZ2AZcREIwdr8"
ADMIN_ID = 901473279  # ТВОЙ ID
SUPPORT_CHAT_ID = ADMIN_ID
 
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
    c.execute('''CREATE TABLE IF NOT EXISTS support
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, message TEXT, date TEXT, answered INTEGER DEFAULT 0)''')
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
 
# --- КОМАНДЫ ---
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
 
    text = f"🌟 Привет! Твой баланс: {user['balance']} звёзд.\n\n"
    text += "🎲 /bet [сумма] [число 1-10] — ставка\n"
    text += "💰 /balance — баланс\n"
    text += "💳 /deposit — пополнить (Telegram Stars)\n"
    text += "💸 /withdraw — вывести звёзды\n"
    text += "🔗 /ref — реферальная ссылка\n"
    text += "🏆 /top — топ игроков\n"
    text += "📞 /support — написать в поддержку\n"
    if user_id == ADMIN_ID:
        text += "\n👑 /admin — админ-панель"
    await update.message.reply_text(text)
 
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    await update.message.reply_text(f"💰 Твой баланс: {user['balance']} звёзд.")
 
async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ /bet [сумма] [число 1-10]")
        return
    try:
        amount = int(args[0])
        guess = int(args[1])
        if amount <= 0 or guess < 1 or guess > 10:
            await update.message.reply_text("❌ Сумма > 0, число от 1 до 10.")
            return
    except:
        await update.message.reply_text("❌ Пример: /bet 5 7")
        return
 
    user = get_user(user_id)
    if user['balance'] < amount:
        await update.message.reply_text("❌ Недостаточно звёзд.")
        return
 
    result = random.randint(1, 10)
    if guess == result:
        win = amount * 2
        update_balance(user_id, win)
        add_transaction(user_id, 'bet_win', win)
        await update.message.reply_text(f"🎉 Угадал! Было {result}. +{win} звёзд!")
    else:
        update_balance(user_id, -amount)
        add_transaction(user_id, 'bet_lose', -amount)
        await update.message.reply_text(f"😢 Не угадал. Было {result}. -{amount} звёзд.")
 
# --- ДЕПОЗИТ (заглушка, позже сделаем реальные Stars) ---
async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💳 Пополнение через Telegram Stars пока в разработке. Используй /addstars [сумма] (только админ) для теста.")
 
# --- ВРЕМЕННАЯ КОМАНДА ДЛЯ ТЕСТА (выдаёт звёзды админу) ---
async def addstars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Недоступно.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("❌ /addstars [сумма]")
        return
    try:
        amount = int(args[0])
    except:
        await update.message.reply_text("❌ Пример: /addstars 100")
        return
    update_balance(ADMIN_ID, amount)
    add_transaction(ADMIN_ID, 'admin_test', amount)
    await update.message.reply_text(f"✅ Добавлено {amount} звёзд админу. Новый баланс: {get_user(ADMIN_ID)['balance']}")
 
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("❌ /withdraw [сумма]")
        return
    try:
        amount = int(args[0])
        if amount <= 0:
            await update.message.reply_text("❌ Сумма > 0")
            return
    except:
        await update.message.reply_text("❌ Пример: /withdraw 10")
        return
 
    user = get_user(user_id)
    if user['balance'] < amount:
        await update.message.reply_text("❌ Недостаточно звёзд.")
        return
 
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO withdraws (user_id, amount, status, date) VALUES (?, ?, ?, ?)',
              (user_id, amount, 'pending', datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    update_balance(user_id, -amount)
    add_transaction(user_id, 'withdraw_pending', -amount)
    await update.message.reply_text(f"✅ Заявка на вывод {amount} звёзд отправлена! Ожидай обработки.")
 
async def ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = f"https://t.me/ZvezdniyFarmBot?start={user_id}"
    await update.message.reply_text(f"🔗 Твоя реферальная ссылка:\n{link}\n\nЗа каждого друга +10 звёзд тебе, +5 ему.")
 
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT id, balance FROM users ORDER BY balance DESC LIMIT 10')
    rows = c.fetchall()
    conn.close()
    text = "🏆 Топ 10 игроков:\n"
    for i, (uid, bal) in enumerate(rows, 1):
        text += f"{i}. ID {uid} — {bal} звёзд\n"
    await update.message.reply_text(text)
 
# --- ПОДДЕРЖКА ---
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args
    if not args:
        await update.message.reply_text("📞 Напиши сообщение для поддержки: /support [текст]")
        return
    message = ' '.join(args)
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('INSERT INTO support (user_id, message, date) VALUES (?, ?, ?)',
              (user_id, message, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ Твоё сообщение отправлено в поддержку! Мы ответим как можно скорее.")
    keyboard = [[InlineKeyboardButton("Ответить", callback_data=f"answer_{user_id}")]]
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 Новое сообщение в поддержку!\nОт: {user_id}\nТекст: {message}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
 
async def support_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = int(query.data.split('_')[1])
    context.user_data['support_user'] = user_id
    await query.edit_message_text(f"✏️ Напиши ответ для пользователя {user_id} (команда /reply [текст])")
 
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Недоступно.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("❌ /reply [текст]")
        return
    if 'support_user' not in context.user_data:
        await update.message.reply_text("❌ Сначала выбери пользователя через кнопку 'Ответить' в сообщении поддержки.")
        return
    user_id = context.user_data['support_user']
    message = ' '.join(args)
    await context.bot.send_message(chat_id=user_id, text=f"📞 Ответ поддержки: {message}")
    await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}.")
 
# --- АДМИНКА ---
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Недоступно.")
        return
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 Выдать звёзды", callback_data="admin_give")],
        [InlineKeyboardButton("📤 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton("📜 История транзакций", callback_data="admin_history")],
        [InlineKeyboardButton("📩 Сообщения в поддержку", callback_data="admin_support")],
    ]
    await update.message.reply_text("👑 Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))
 
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if user_id != ADMIN_ID:
        await query.edit_message_text("⛔ Недоступно.")
        return
 
    if query.data == "admin_stats":
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        users = c.fetchone()[0]
        c.execute('SELECT SUM(balance) FROM users')
        total = c.fetchone()[0] or 0
        conn.close()
        await query.edit_message_text(f"📊 Статистика:\nВсего игроков: {users}\nОбщий баланс: {total} звёзд")
 
    elif query.data == "admin_give":
        await query.edit_message_text("💡 Используй /give [ID] [сумма]")
 
    elif query.data == "admin_withdraws":
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, user_id, amount FROM withdraws WHERE status = "pending"')
        rows = c.fetchall()
        conn.close()
        if not rows:
            await query.edit_message_text("✅ Заявок нет.")
            return
        text = "📤 Заявки на вывод:\n"
        for w_id, uid, amt in rows:
            text += f"ID {w_id} | Пользователь {uid} | {amt} звёзд\n"
        text += "\nИспользуй /approve [ID заявки] или /reject [ID заявки]"
        await query.edit_message_text(text)
 
    elif query.data == "admin_history":
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT user_id, type, amount, date FROM transactions ORDER BY id DESC LIMIT 10')
        rows = c.fetchall()
        conn.close()
        text = "📜 Последние 10 транзакций:\n"
        for uid, typ, amt, date in rows:
            text += f"{date} | {uid} | {typ} | {amt}\n"
        await query.edit_message_text(text)
 
    elif query.data == "admin_support":
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute('SELECT id, user_id, message, date FROM support WHERE answered = 0 ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        if not rows:
            await query.edit_message_text("✅ Новых обращений нет.")
            return
        text = "📩 Новые сообщения в поддержку:\n"
        for s_id, uid, msg, date in rows:
            text += f"ID {s_id} | От {uid} | {date}\n{msg}\n\n"
        await query.edit_message_text(text)
 
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
    await update.message.reply_text(f"✅ Пользователю {target} выдано {amount} звёзд.")
 
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Недоступно.")
        return
    args = context.args
    if not args:
        await update.message.reply_text("❌ /approve [ID заявки]")
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
        await update.message.reply_text("❌ /reject [ID заявки]")
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
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("bet", bet))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("addstars", addstars))
    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("ref", ref))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(CommandHandler("reply", reply))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("give", give))
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("reject", reject))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="admin_"))
    app.add_handler(CallbackQueryHandler(support_answer, pattern="answer_"))
    print("Бот запущен...")
    app.run_polling()
 
if __name__ == "__main__":
    main()
