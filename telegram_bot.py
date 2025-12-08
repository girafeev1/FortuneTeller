import os
import random
from datetime import datetime
from typing import List, Optional, Dict, Set

import pandas as pd
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    JobQueue,
    filters,
)


CSV_PATH = os.environ.get("MARK6_CSV_PATH", "merged_results.csv")
CSV_URL = os.environ.get(
    "MARK6_CSV_URL",
    "https://raw.githubusercontent.com/girafeev1/FortuneTeller/main/merged_results.csv",
)

GENERATE_PROMPT_TEXT = "Would you like to generate a unique combination?"


def load_data() -> pd.DataFrame:
    # Prefer online CSV so the bot follows the deployed data
    try:
        return pd.read_csv(CSV_URL)
    except Exception:
        # Fallback to local file if network/unavailable
        return pd.read_csv(CSV_PATH)


def generate_unique_combination(df: pd.DataFrame) -> List[int]:
    existing_combinations = set()
    for _, row in df.iterrows():
        combination = tuple(
            sorted(
                [
                    row["num_1"],
                    row["num_2"],
                    row["num_3"],
                    row["num_4"],
                    row["num_5"],
                    row["num_6"],
                ]
            )
        )
        existing_combinations.add(combination)

    while True:
        new_combination = tuple(sorted(random.sample(range(1, 50), 6)))
        if new_combination not in existing_combinations:
            return list(new_combination)


def find_combination(df: pd.DataFrame, numbers: List[int]) -> Optional[Dict]:
    search_combination = tuple(sorted(numbers))
    for _, row in df.iterrows():
        combination = tuple(
            sorted(
                [
                    row["num_1"],
                    row["num_2"],
                    row["num_3"],
                    row["num_4"],
                    row["num_5"],
                    row["num_6"],
                ]
            )
        )
        if combination == search_combination:
            return {
                "date": row["date"],
                "draw_number": row["draw_number"],
                "numbers": combination,
                "bonus": row["bonus"],
            }
    return None


def get_latest_draw(df: pd.DataFrame) -> Optional[Dict]:
    if df is None or df.empty:
        return None
    row = df.iloc[0]
    numbers = [
        row["num_1"],
        row["num_2"],
        row["num_3"],
        row["num_4"],
        row["num_5"],
        row["num_6"],
    ]
    return {
        "date": row["date"],
        "draw_number": row["draw_number"],
        "numbers": numbers,
        "bonus": row["bonus"],
    }


def parse_numbers(text: str) -> List[int]:
    cleaned = text.replace(",", " ").replace(";", " ")
    parts = [p for p in cleaned.split() if p]
    nums = [int(p) for p in parts]
    if len(nums) != 6:
        raise ValueError("Please provide exactly 6 numbers.")
    return nums


def format_date_human(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return date_str


def subscribe_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if not chat:
        return
    subs: Set[int] = context.application.bot_data.setdefault("subscribed_chats", set())
    subs.add(chat.id)


def generate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("Generate", callback_data="generate")]]
    )


async def send_generate_prompt(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    chat = update.effective_chat
    if not chat:
        return
    await context.bot.send_message(
        chat_id=chat.id,
        text=GENERATE_PROMPT_TEXT,
        reply_markup=generate_keyboard(),
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subscribe_chat(update, context)

    header = (
        "Iiiiccchh Aaaaaaiiiiiiiiichhhhhh ugggghhhhhhhhhh\n"
        "INGGGG INGGGGGGG UNNNNGGGG UNGGGGGGGG OOOOOOONNNN YOONNNGGGGGGGGG"
    )

    # Bubble 1: header/scream
    await update.message.reply_text(header)

    # Prepare latest draw info
    try:
        df = load_data()
        latest = get_latest_draw(df)
    except Exception:
        latest = None

    if latest:
        date_str = format_date_human(latest["date"])
        numbers_str = ", ".join(str(n) for n in latest["numbers"])
        last_draw_text = (
            "Last Drawn Result:\n"
            f"Date: {date_str} (Draw #{latest['draw_number']})\n"
            f"Numbers: {numbers_str}\n"
            f"Extra:   {latest['bonus']}"
        )
        # Bubble 2: last drawn result
        await update.message.reply_text(last_draw_text)

    # Bubble 3: how to generate (text only)
    generate_text = (
        "Type /generate or\n"
        "Press the Generate button below for a unique combintaion"
    )
    await update.message.reply_text(generate_text)

    # Bubble 4: 'or'
    await update.message.reply_text("or")

    # Bubble 5: how to search
    search_text = (
        "Enter a combination of 6 numbers and check if it has been drawn\n"
        "1, 26, 39, 47, 31, 50 etc."
    )
    await update.message.reply_text(search_text)

    # Final bubble: generate prompt with button
    await send_generate_prompt(update, context)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "generate":
        # Ensure this chat is subscribed for future draw notifications
        subscribe_chat(update, context)
        loading_msg = await query.message.reply_text("Loading...")
        try:
            df = load_data()
            combo = generate_unique_combination(df)
            await loading_msg.edit_text(
                f"Your unique combination is: {', '.join(str(n) for n in combo)}"
            )
        except Exception:
            await loading_msg.edit_text(
                "Sorry, something went wrong while generating a combination. "
                "Please try again in a moment."
            )
        # Keep generate button visible
        await send_generate_prompt(update, context)


async def generate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subscribe_chat(update, context)
    loading_msg = await update.message.reply_text("Loading...")
    try:
        df = load_data()
        combo = generate_unique_combination(df)
        await loading_msg.edit_text(
            f"Your unique combination is: {', '.join(str(n) for n in combo)}"
        )
    except Exception:
        await loading_msg.edit_text(
            "Sorry, something went wrong while generating a combination. "
            "Please try again in a moment."
        )
    # Keep generate button visible
    await send_generate_prompt(update, context)


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subscribe_chat(update, context)
    if context.args:
        text = " ".join(context.args)
    else:
        await update.message.reply_text(
            "Please provide 6 numbers, e.g.:\n"
            "/search 1 2 3 4 5 6\n"
            "or\n"
            "/search 1,2,3,4,5,6"
        )
        return

    loading_msg = await update.message.reply_text("Loading...")

    try:
        numbers = parse_numbers(text)
    except ValueError as e:
        await loading_msg.edit_text(str(e))
        await send_generate_prompt(update, context)
        return

    try:
        df = load_data()
        result = find_combination(df, numbers)
    except Exception:
        await loading_msg.edit_text(
            "Sorry, something went wrong while checking that combination. "
            "Please try again in a moment."
        )
        await send_generate_prompt(update, context)
        return

    if result:
        numbers_str = ", ".join(str(n) for n in result["numbers"])
        await loading_msg.edit_text(
            "This combination HAS been drawn.\n"
            f"Date: {result['date']} (Draw #{result['draw_number']})\n"
            f"Numbers: {numbers_str}\n"
            f"Bonus: {result['bonus']}"
        )
    else:
        await loading_msg.edit_text(
            "This combination has NEVER been drawn.\n"
            f"Numbers checked: {', '.join(str(n) for n in sorted(numbers))}"
        )

    # Keep generate button visible
    await send_generate_prompt(update, context)


async def plain_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    subscribe_chat(update, context)

    text = update.message.text
    loading_msg = await update.message.reply_text("Loading...")

    try:
        numbers = parse_numbers(text)
    except ValueError:
        # Not a valid 6-number combination; gently hint how to use it.
        await loading_msg.edit_text(
            "To check a combination, send 6 numbers like:\n"
            "1 2 3 4 5 6\n"
            "or\n"
            "1,2,3,4,5,6"
        )
        await send_generate_prompt(update, context)
        return

    try:
        df = load_data()
        result = find_combination(df, numbers)
    except Exception:
        await loading_msg.edit_text(
            "Sorry, something went wrong while checking that combination. "
            "Please try again in a moment."
        )
        await send_generate_prompt(update, context)
        return

    if result:
        numbers_str = ", ".join(str(n) for n in result["numbers"])
        await loading_msg.edit_text(
            "This combination HAS been drawn.\n"
            f"Date: {result['date']} (Draw #{result['draw_number']})\n"
            f"Numbers: {numbers_str}\n"
            f"Bonus: {result['bonus']}"
        )
    else:
        await loading_msg.edit_text(
            "This combination has NEVER been drawn.\n"
            f"Numbers checked: {', '.join(str(n) for n in sorted(numbers))}"
        )

    # Keep generate button visible
    await send_generate_prompt(update, context)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Please set TELEGRAM_BOT_TOKEN environment variable.")

    application = ApplicationBuilder().token(token).build()

    # Initialize last known draw number for change detection
    try:
        df = load_data()
        latest = get_latest_draw(df)
        if latest:
            application.bot_data["last_draw_number"] = latest["draw_number"]
    except Exception:
        application.bot_data["last_draw_number"] = None

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_handler))

    # Periodically check for new draws and notify subscribers
    job_queue: JobQueue = application.job_queue

    async def check_for_new_draw(context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            df = load_data()
            latest = get_latest_draw(df)
        except Exception:
            return

        if not latest:
            return

        app = context.application
        last_draw_number = app.bot_data.get("last_draw_number")
        if last_draw_number == latest["draw_number"]:
            return

        app.bot_data["last_draw_number"] = latest["draw_number"]

        subs: Set[int] = app.bot_data.get("subscribed_chats", set())
        if not subs:
            return

        date_str = format_date_human(latest["date"])
        numbers_str = ", ".join(str(n) for n in latest["numbers"])
        message = (
            "New Mark 6 draw!\n"
            f"Date: {date_str} (Draw #{latest['draw_number']})\n"
            f"Numbers: {numbers_str}\n"
            f"Extra:   {latest['bonus']}"
        )

        for chat_id in subs:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=GENERATE_PROMPT_TEXT,
                    reply_markup=generate_keyboard(),
                )
            except Exception:
                continue

    # Check once an hour; you can tune this if you like
    job_queue.run_repeating(check_for_new_draw, interval=3600, first=300)

    application.run_polling()


if __name__ == "__main__":
    main()
