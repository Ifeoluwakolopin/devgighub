import datetime
import logging
import time
import string
import json
import asyncio
import pymongo
import telegram
from telegram import LinkPreviewOptions
from telegram.ext import Application
from telegram.ext import CommandHandler
from telegram.ext import MessageHandler, filters

config = json.load(open("config.json"))
application = Application.builder().token(config["token"]).build()
bot = application.bot
dispatcher = application
client = pymongo.MongoClient(config["db"]["host"], config["db"]["port"])
db = client[config["db"]["db_name"]]
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def parse_stack(stack):
    stack = stack.strip().lower()
    accepted_chars = string.ascii_lowercase + string.digits + "-/+#. "
    return "".join([i for i in stack if i in accepted_chars])


async def send_broadcast(args, semaphore):
    async with semaphore:
        try:
            await bot.send_message(chat_id=args[0], text=args[1],
                                   link_preview_options=LinkPreviewOptions(is_disabled=True))
        except Exception as e:
            if str(e) in ("Forbidden: bot was blocked by the user", "bot was blocked by the user"):
                return args[0]


async def start(update, context):
    chat_id = update.effective_chat.id
    if not db.users.find_one({"chat_id": chat_id}):
        db.users.insert_one(
            {"chat_id": chat_id, "last_command": None, "admin": False, "mute": False, "date": datetime.datetime.now()})
    db.users.update_one({"chat_id": chat_id}, {"$set": {"active": True}})
    await context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["start"].format(update["message"]["chat"]["first_name"]), parse_mode="Markdown", link_preview_options=LinkPreviewOptions(is_disabled=True))
    await context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["menu"])
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


async def menu(update, context):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["menu"])
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


async def view_stack(update, context):
    chat_id = update.effective_chat.id
    stack = list(db.user_stack.find({"chat_id": chat_id}))
    if stack == []:
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["empty_stack"])
    else:
        stack = [i["stack"].capitalize() for i in stack]
        stack_message = config["messages"]["stack"].format(
            ", ".join(stack))
        await context.bot.send_message(
            chat_id=chat_id, text=stack_message)
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


async def add_stack(update, context):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["add_stack"])
    last_command = "add_stack"
    db.users.update_one({"chat_id": chat_id}, {
                        "$set": {"last_command": last_command}})


async def remove_stack(update, context):
    chat_id = update.effective_chat.id
    stack = list(db.user_stack.find({"chat_id": chat_id}))
    if stack == []:
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["empty_stack"])
    else:
        stack = [i["stack"].capitalize() for i in stack]
        stack_message = config["messages"]["remove_stack"].format(
            ", ".join(stack))
        await context.bot.send_message(
            chat_id=chat_id, text=stack_message)
        last_command = "remove_stack"
        db.users.update_one({"chat_id": chat_id}, {
                            "$set": {"last_command": last_command}})


async def get_random(update, context):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["get_random"])
    last_command = "get_random"
    db.users.update_one({"chat_id": chat_id}, {
                        "$set": {"last_command": last_command}})


async def stats(update, context):
    chat_id = update.effective_chat.id
    total_users = db.users.count_documents({})
    total_jobs = db.jobs.count_documents({})

    total_job_stack = db.user_stack.count_documents({})
    user_stack_stats = ""
    for i in list(db.user_stack.aggregate([{"$group": {"_id": "$stack", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}, {"$limit": 10}])):
        user_stack_stats += "`{}` - {:.2f}%\n".format(i["_id"].capitalize(),
                                                      i["count"] / total_job_stack * 100)

    await context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["stats"].format(total_jobs, total_users, user_stack_stats, time.strftime("%d/%m/%Y %H:%M:%S UTC")), parse_mode="Markdown")
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


async def donate(update, context):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id, text=config["messages"]["donate"])
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


async def broadcast(update, context):
    chat_id = update.effective_chat.id
    admin_status = db.users.find_one({"chat_id": chat_id, "admin": True})
    if admin_status:
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["broadcast"].format(db.users.count_documents({})))
        db.users.update_one({"chat_id": chat_id}, {
                            "$set": {"last_command": "broadcast"}})

    else:
        db.users.update_one({"chat_id": chat_id}, {
                            "$set": {"last_command": None}})


async def mute(update, context):
    chat_id = update.effective_chat.id
    bot_user = db.users.find_one({"chat_id": chat_id})
    if bot_user["mute"]:
        db.users.update_one({"chat_id": chat_id}, {"$set": {"mute": False}})
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["unmuted"])
    else:
        db.users.update_one({"chat_id": chat_id}, {"$set": {"mute": True}})
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["muted"])


async def echo(update, context):
    chat_id = update.effective_chat.id
    bot_user = db.users.find_one({"chat_id": chat_id})
    last_command = bot_user["last_command"] if bot_user != None else None
    if last_command == "add_stack":
        stack = ",".join(update.message.text.split("\n"))
        stack = [parse_stack(i)
                 for i in stack.split(",") if i.strip() != ""]
        for i in stack:
            db.user_stack.delete_many({"chat_id": chat_id, "stack": i})
        db.user_stack.insert_many(
            [{"chat_id": chat_id, "stack": i} for i in stack])
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["updated_stack"])
    elif last_command == "remove_stack":
        stack = ",".join(update.message.text.split("\n"))
        stack = [parse_stack(i)
                 for i in stack.split(",") if i.strip() != ""]
        for i in stack:
            db.user_stack.delete_many({"chat_id": chat_id, "stack": i})
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["updated_stack"])
    elif last_command == "get_random":
        stack = update.message.text.strip().lower()
        pipeline = [{"$match": {"date": {"$gte": datetime.datetime.now() - datetime.timedelta(
            days=14)}, "stacks": {"$in": [stack]}}}, {"$sample": {"size": 10}}]
        jobs = ""
        for i in db.jobs.aggregate(pipeline):
            jobs += "Role: {}\nLink: {}\nDate Posted: {}\n\n".format(
                i["info"]["role"], i["href"], "{}/{}/{}".format(i["date"].day, i["date"].month, i["date"].year))
        if jobs == "":
            jobs = config["messages"]["empty_random"]
        await context.bot.send_message(
            chat_id=chat_id, text=jobs, link_preview_options=LinkPreviewOptions(is_disabled=True))
    elif last_command == "broadcast":
        semaphore = asyncio.Semaphore(5)
        blocked_users = await asyncio.gather(*(
            send_broadcast([i["chat_id"], update.message.text], semaphore)
            for i in db.users.find({"active": True})))
        db.users.update_many({"chat_id": {"$in": [i for i in blocked_users if i != None]}}, {
                             "$set": {"active": False}})
        users_count = db.users.count_documents({})
        total_delivered = db.users.count_documents({"active": True})
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["finished_broadcast"].format(users_count, total_delivered, total_delivered / users_count * 100))
    else:
        if bot_user["admin"]:
            await context.bot.send_message(
                chat_id=chat_id, text=update.message.text, link_preview_options=LinkPreviewOptions(is_disabled=True))
        await context.bot.send_message(
            chat_id=chat_id, text=config["messages"]["unknown"])
    db.users.update_one({"chat_id": chat_id}, {"$set": {"last_command": None}})


start_handler = CommandHandler("start", start)
menu_handler = CommandHandler("menu", menu)
stats_handler = CommandHandler("stats", stats)
donate_handler = CommandHandler("donate", donate)
view_stack_handler = CommandHandler("view_stack", view_stack)
add_stack_handler = CommandHandler("add_stack", add_stack)
remove_stack_handler = CommandHandler("remove_stack", remove_stack)
get_random_handler = CommandHandler("get_random", get_random)
mute_handler = CommandHandler("mute", mute)
broadcast_handler = CommandHandler("broadcast", broadcast)
echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)

dispatcher.add_handler(start_handler)
dispatcher.add_handler(menu_handler)
dispatcher.add_handler(donate_handler)
dispatcher.add_handler(stats_handler)
dispatcher.add_handler(view_stack_handler)
dispatcher.add_handler(add_stack_handler)
dispatcher.add_handler(remove_stack_handler)
dispatcher.add_handler(get_random_handler)
dispatcher.add_handler(mute_handler)
dispatcher.add_handler(broadcast_handler)
dispatcher.add_handler(echo_handler)

if __name__ == "__main__":
    application.run_polling()
