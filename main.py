import os
import re
import requests
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update
import logging

logging.basicConfig(level=logging.INFO)

# === TELEGRAM CONFIG ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

# === ATERNOS CONFIG ===
ATERNOS_USER = os.getenv("ATERNOS_USER")
ATERNOS_PASS = os.getenv("ATERNOS_PASS")
ATERNOS_SERVER_NAME = os.getenv("ATERNOS_SERVER_NAME")

# === GLOBAL VARS ===
session = None


def login_to_aternos():
    global session
    if session:
        return session

    session = requests.Session()
    login_url = "https://aternos.org/login"
    resp = session.get(login_url)
    token_match = re.search(r'"token"\s*:\s*"([^"]+)"', resp.text)
    if not token_match:
        raise Exception("Не удалось получить токен авторизации.")
    token = token_match.group(1)

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


def get_server_status():
    sess = login_to_aternos()
    servers_page = sess.get("https://aternos.org/servers").text
    server_id_match = re.search(rf'data-server="([^"]*)"[^>]*title="{re.escape(ATERNOS_SERVER_NAME)}"', servers_page)
    if not server_id_match:
        raise Exception("Сервер не найден на Aternos.")

    server_id = server_id_match.group(1)
    status_resp = sess.get(f"https://aternos.org/server/status/{server_id}.json").json()

    return status_resp


def serv_start(update: Update, context: CallbackContext):
    try:
        sess = login_to_aternos()
        status_data = get_server_status()
        server_id = status_data["id"]

        start_resp = sess.get(f"https://aternos.org/server/start/{server_id}.ajax").json()
        if start_resp.get("success"):
            update.message.reply_text("✅ Сервер запущен!")
        else:
            update.message.reply_text("❌ Ошибка при запуске сервера.")
    except Exception as e:
        update.message.reply_text(f"💥 Ошибка: {e}")


def serv_stop(update: Update, context: CallbackContext):
    try:
        sess = login_to_aternos()
        status_data = get_server_status()
        server_id = status_data["id"]

        stop_resp = sess.get(f"https://aternos.org/server/stop/{server_id}.ajax").json()
        if stop_resp.get("success"):
            update.message.reply_text("🔴 Сервер выключен.")
        else:
            update.message.reply_text("❌ Ошибка при выключении сервера.")
    except Exception as e:
        update.message.reply_text(f"💥 Ошибка: {e}")


def check_status(update: Update, context: CallbackContext):
    try:
        status_data = get_server_status()
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
        update.message.reply_text(msg)
    except Exception as e:
        update.message.reply_text(f"💥 Ошибка: {e}")


def main():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("serv_start", serv_start))
    dp.add_handler(CommandHandler("serv_stop", serv_stop))
    dp.add_handler(CommandHandler("status", check_status))

    print("🚀 Бот запущен на polling...")
    updater.start_polling(drop_pending_updates=True)
    updater.idle()


if __name__ == "__main__":
    main()
