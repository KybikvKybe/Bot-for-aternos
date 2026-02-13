import os
import re
import requests
from telegram import Update
from telegram.ext import Application, ContextTypes
from flask import Flask, request

# === TELEGRAM CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Пример: https://mybot.fly.dev/webhook
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # ID админа или канала

# === ATERNOS CONFIG ===
ATERNOS_USER = os.getenv("ATERNOS_USER")  # Логин
ATERNOS_PASS = os.getenv("ATERNOS_PASS")  # Пароль
ATERNOS_SERVER_NAME = os.getenv("ATERNOS_SERVER_NAME")  # Имя сервера

# === GLOBAL VARS ===
session = None

app = Flask(__name__)

async def login_to_aternos():
    global session
    if session:
        return session

    session = requests.Session()
    login_url = "https://aternos.org/login"
    resp = session.get(login_url)
    # Извлекаем токен
    token_match = re.search(r'"token"\s*:\s*"([^"]+)"', resp.text)
    if not token_match:
        raise Exception("Не удалось получить токен авторизации.")
    token = token_match.group(1)

    # Авторизация
    login_data = {
        "user": ATERNOS_USER,
        "password": ATERNOS_PASS,
        "headless": "true",
        "action": "login",
        "token": token
    }
    r = session.post(f"{login_url}.ajax", data=login_data)
    if "success" not in r.json():
        raise Exception("Ошибка входа в Aternos.")

    return session


async def get_server_status():
    sess = await login_to_aternos()
    servers_page = sess.get("https://aternos.org/servers").text
    server_id_match = re.search(rf'data-server="([^"]*)"[^>]*title="{re.escape(ATERNOS_SERVER_NAME)}"', servers_page)
    if not server_id_match:
        raise Exception("Сервер не найден на Aternos.")

    server_id = server_id_match.group(1)
    status_resp = sess.get(f"https://aternos.org/server/status/{server_id}.json").json()

    return status_resp


async def start_server(update: Update, context):
    try:
        sess = await login_to_aternos()
        status_data = await get_server_status()
        server_id = status_data["id"]

        # Запускаем
        start_resp = sess.get(f"https://aternos.org/server/start/{server_id}.ajax").json()
        if start_resp.get("success"):
            await update.effective_message.reply_text("✅ Сервер запущен!")
        else:
            await update.effective_message.reply_text("❌ Ошибка при запуске сервера.")
    except Exception as e:
        await update.effective_message.reply_text(f"💥 Ошибка: {e}")


async def stop_server(update: Update, context):
    try:
        sess = await login_to_aternos()
        status_data = await get_server_status()
        server_id = status_data["id"]

        # Останавливаем
        stop_resp = sess.get(f"https://aternos.org/server/stop/{server_id}.ajax").json()
        if stop_resp.get("success"):
            await update.effective_message.reply_text("🔴 Сервер выключен.")
        else:
            await update.effective_message.reply_text("❌ Ошибка при выключении сервера.")
    except Exception as e:
        await update.effective_message.reply_text(f"💥 Ошибка: {e}")


async def check_status(update: Update, context):
    try:
        status_data = await get_server_status()
        status = status_data["status"]
        players = status_data["players"]["online"]
        ip = status_data["ip"]
        port = status_data["port"]

        msg = f"""
📊 Статус сервера:
🔹 Статус: {status}
🔹 Игроков онлайн: {players}
🔹 IP: {ip}:{port}
        """
        await update.effective_message.reply_text(msg)
    except Exception as e:
        await update.effective_message.reply_text(f"💥 Ошибка: {e}")


@app.route('/webhook', methods=['POST'])
def webhook():
    update_json = request.get_json()
    update = Update.de_json(update_json)
    app_bot.process_update(update)
    return "OK"


if __name__ == "__main__":
    app_bot = Application.builder().token(BOT_TOKEN).build()

    app_bot.add_handler(CommandHandler("start_server", start_server))
    app_bot.add_handler(CommandHandler("stop_server", stop_server))
    app_bot.add_handler(CommandHandler("status", check_status))

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8000)))