import random
import sqlite3
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
 
TOKEN = "8820171167:AAGiEb-WodNUyhPTMdbdUGnZ2AZcREIwdr8"
 
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
 
def get_balance(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
    row = c.fetchone()
    if row:
        return row[0]
    else:
        c.execute('INSERT INTO users (id, balance) VALUES (?, ?)', (user_id, 0))
        conn.commit()
        return 0
 
def update_balance(user_id, amount):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()
 
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = get_balance(user_id)
    await update.message.reply_text(f"Привет! Твой баланс: {bal} звёзд.\n/bet сумма число — сделать ставку\n/balance — баланс")
 
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bal = get_balance(user_id)
    await update.message.reply_text(f"Твой баланс: {bal} звёзд.")
 
async def bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        amount = int(context.args[0])
        guess = int(context.args[1])
        if amount <= 0 or guess < 1 or guess > 10:
            await update.message.reply_text("Сумма > 0, число от 1 до 10.")
            return
    except:
        await update.message.reply_text("Пример: /bet 5 7")
        return
    bal = get_balance(user_id)
    if bal < amount:
        await update.message.reply_text("Не хватает звёзд.")
        return
    result = random.randint(1, 10)
    if guess == result:
        win = amount * 2
        update_balance(user_id, win)
        await update.message.reply_text(f"Угадал! Было {result}. +{win} звёзд!")
    else:
        update_balance(user_id, -amount)
        await update.message.reply_text(f"Не угадал. Было {result}. -{amount} звёзд.")
 
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("bet", bet))
    print("Бот запущен...")
    app.run_polling()
 
if __name__ == "__main__":
    main()
