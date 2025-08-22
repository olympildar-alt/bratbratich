import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
YC_FOLDER_ID = os.environ["YC_FOLDER_ID"]
YC_ACCESS_KEY_ID = os.environ["YC_ACCESS_KEY_ID"]
YC_SECRET_ACCESS_KEY = os.environ["YC_SECRET_ACCESS_KEY"]
WEBHOOK_PATH = f"/webhook/{TELEGRAM_BOT_TOKEN}"
WEBHOOK_URL = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}{WEBHOOK_PATH}"

app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

def get_iam_token():
    url = "https://sts.api.cloud.yandex.net/iam/v1/tokens"
    headers = {"Content-Type": "application/json"}
    data = {
        "accessKeyId": YC_ACCESS_KEY_ID,
        "secretAccessKey": YC_SECRET_ACCESS_KEY
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json().get("iamToken")

def get_sarcastic_reply(user_message):
    try:
        iam_token = get_iam_token()
        url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
        headers = {
            "Authorization": f"Bearer {iam_token}",
            "Content-Type": "application/json"
        }
        body = {
            "modelUri": f"gpt://{YC_FOLDER_ID}/yandexgpt/latest",
            "completionOptions": {
                "temperature": 0.7,
                "maxTokens": 200
            },
            "messages": [
                {"role": "system", "text": "Ты отвечаешь саркастично, язвительно и с приколом на тему сломанных велосипедов и дорогих ремонтов у Раиля а так же на тему пешей ставки 169 рублей."},
                {"role": "user", "text": user_message}
            ]
        }
        response = requests.post(url, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()
        return result["result"]["alternatives"][0]["message"]["text"]
    except Exception as e:
        return f"Ошибка от нейросети: {e}"

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    reply_text = get_sarcastic_reply(user_text)
    await update.message.reply_text(reply_text)

@app.route("/")
def index():
    return "Брат тут. Webhook OK."

@app.post(WEBHOOK_PATH)
async def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return "ok"

if __name__ == "__main__":
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    telegram_app.initialize()
    telegram_app.bot.set_webhook(WEBHOOK_URL)
    app.run(host="0.0.0.0", port=10000)
