import json
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.environ["BOT_TOKEN"]  # el token de BotFather
DB = "pelis.json"

# IDs d'usuari de Telegram que poden afegir pel·lícules (separats per comes)
OWNER_IDS = {
    int(x) for x in os.environ.get("OWNER_IDS", "").split(",") if x.strip()
}

# Caràtula/pel·lícula pendents d'aparellar, per xat
pending = {}


def load():
    if os.path.exists(DB):
        with open(DB) as f:
            return json.load(f)
    return {"next": 1, "items": {}}


def save(db):
    with open(DB, "w") as f:
        json.dump(db, f)


async def receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if msg.from_user.id not in OWNER_IDS:
        return  # els altres no poden afegir res
    p = pending.setdefault(msg.chat_id, {})

    if msg.photo:
        p["cover"] = msg.photo[-1].file_id
    elif msg.video:
        p["movie"] = msg.video.file_id
        p["kind"] = "video"
    elif msg.document:
        p["movie"] = msg.document.file_id
        p["kind"] = "document"

    if "cover" in p and "movie" in p:
        db = load()
        n = db["next"]
        db["items"][str(n)] = dict(p)
        db["next"] = n + 1
        save(db)
        pending.pop(msg.chat_id, None)
        await msg.reply_text(
            f"✅ url={n}\nhttps://t.me/{ctx.bot.username}?start={n}"
        )
    else:
        falta = "la pel·lícula" if "cover" in p else "la caràtula"
        await msg.reply_text(f"Rebut. Ara envia {falta}.")


async def send_item(msg, n: str):
    item = load()["items"].get(n)
    if not item:
        await msg.reply_text(f"No existeix url={n}")
        return
    await msg.reply_photo(item["cover"], caption=f"url={n}")
    if item["kind"] == "video":
        await msg.reply_video(item["movie"])
    else:
        await msg.reply_document(item["movie"])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if ctx.args:
        await send_item(update.effective_message, ctx.args[0])
    else:
        await update.effective_message.reply_text(
            "Envia'm la caràtula (foto) i la pel·lícula (vídeo o fitxer)."
        )


async def get(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if ctx.args:
        await send_item(update.effective_message, ctx.args[0])


async def myid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        f"El teu ID: {update.effective_user.id}"
    )


async def lista(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    db = load()
    txt = "\n".join(f"url={n}" for n in db["items"]) or "Buit"
    await update.effective_message.reply_text(txt)


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("get", get))
    app.add_handler(CommandHandler("list", lista))
    app.add_handler(CommandHandler("id", myid))
    app.add_handler(
        MessageHandler(
            filters.PHOTO | filters.VIDEO | filters.Document.ALL, receive
        )
    )
    app.run_polling()


if __name__ == "__main__":
    main()
