import os
import requests
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
import asyncio

app = FastAPI()
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
YC_FOLDER_ID = os.environ["YC_FOLDER_ID"]
YC_ACCESS_KEY_ID = os.environ["YC_ACCESS_KEY_ID"]
YC_SECRET_ACCESS_KEY = os.environ["YC_SECRET_ACCESS_KEY"]
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}{WEBHOOK_PATH}"

telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

def get_iam_token():
    resp = requests.post(
        "https://sts.api.cloud.yandex.net/iam/v1/tokens",
        headers={"Content-Type": "application/json"},
        json={"accessKeyId": YC_ACCESS_KEY_ID, "secretAccessKey": YC_SECRET_ACCESS_KEY}
    ); resp.raise_for_status()
    return resp.json()["iamToken"]

def get_sarcastic_reply(user_message):
    try:
        iam_token = get_iam_token()
        resp = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/completion",
            headers={"Authorization": f"Bearer {iam_token}", "Content-Type": "application/json"},
            json={
                "modelUri": f"gpt://{YC_FOLDER_ID}/yandexgpt/latest",
                "completionOptions": {"temperature": 0.7, "maxTokens": 200},
                "messages": [
                    {"role": "system", "text": "Ты отвечаешь саркастично и остроумно."},
                    {"role": "user", "text": user_message}
                ]
            }
        ); resp.raise_for_status()
        return resp.json()["result"]["alternatives"][0]["message"]["text"]
    except Exception as e:
        return f"Ошибка от нейросети: {e}"

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = get_sarcastic_reply(update.message.text)
    await update.message.reply_text(text)

@app.post(WEBHOOK_PATH)
async def webhook_handler(req: Request):
    data = await req.json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return PlainTextResponse("ok")

@app.on_event("startup")
async def on_startup():
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
    await telegram_app.initialize()
    await telegram_app.bot.set_webhook(WEBHOOK_URL)

@app.on_event("shutdown")
async def on_shutdown():
    await telegram_app.shutdown()
