import os
import random
from datetime import datetime
from html import escape as html_escape
from typing import List, Optional, Dict, Set

import pandas as pd
import requests
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.constants import ParseMode
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

HKJC_GRAPHQL_URL = "https://info.cld.hkjc.com/graphql/base/"

# Minutes before close time to notify users before draw closes
REMINDER_THRESHOLDS_MIN = [60, 30, 15, 12, 10, 7, 5]


def escape_html(value: object) -> str:
    return html_escape("" if value is None else str(value), quote=False)

_ZWSP = "\u200b"


def format_bold_italic(text: str) -> str:
    # Telegram entities must be properly nested and must not overlap.
    # To get bold+italic on the same visible text reliably, we pad the outer <b>
    # with zero-width spaces so the <i> entity is strictly nested.
    return f"<b>{_ZWSP}<i>{escape_html(text)}</i>{_ZWSP}</b>"


def get_generate_prompt_html() -> str:
    return (
        "Enter a combination of "
        f"{format_bold_italic('6 numbers')} "
        "and check if it has been drawn or Press "
        f"{format_bold_italic('Generate')} "
        "below for a unique number combination"
    )


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


def fetch_hkjc_draws() -> Optional[Dict]:
    payload = {
        "operationName": "marksix",
        "variables": {},
        "query": (
            "fragment lotteryDrawsFragment on LotteryDraw {\n"
            "  id\n  year\n  no\n  openDate\n  closeDate\n  drawDate\n  status\n"
            "  snowballCode\n  snowballName_en\n  snowballName_ch\n"
            "  lotteryPool {\n"
            "    sell\n    status\n    totalInvestment\n    jackpot\n    unitBet\n"
            "    estimatedPrize\n    derivedFirstPrizeDiv\n"
            "    lotteryPrizes { type winningUnit dividend }\n"
            "  }\n"
            "  drawResult { drawnNo xDrawnNo }\n"
            "}\n"
            "fragment lotteryStatFragment on LotteryStat {\n"
            "  year\n  no\n  drawDate\n  drawnNumbers { lastDrawnIn totalNumber drawnNo }\n"
            "}\n"
            "query marksix {\n"
            "  lotteryDraws { ...lotteryDrawsFragment }\n"
            "  lotteryStats { ...lotteryStatFragment }\n"
            "}\n"
        ),
    }
    try:
        res = requests.post(HKJC_GRAPHQL_URL, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("data", {})
    except Exception:
        return None


def get_latest_hkjc_draw(draws: List[Dict]) -> Optional[Dict]:
    results = [d for d in draws if d.get("status", "").lower() == "result"]
    if not results:
        return None
    results.sort(key=lambda d: d.get("drawDate", "") or d.get("id", ""), reverse=True)
    return results[0]


def get_next_hkjc_draw(draws: List[Dict]) -> Optional[Dict]:
    candidates = [
        d
        for d in draws
        if d.get("status", "").lower() in {"defined", "startsell", "selling", "pending"}
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda d: d.get("closeDate", "") or d.get("drawDate", ""))
    return candidates[0]


def format_date_human(date_str: str) -> str:
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return date_str


def format_hkjc_dt(dt_str: str) -> str:
    """Format HKJC ISO-ish date string to 'MMM DD, YYYY HH:MM' without timezone."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return dt_str


def format_currency(val: str) -> str:
    try:
        return f"{int(val):,}"
    except Exception:
        return val


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
        text=get_generate_prompt_html(),
        parse_mode=ParseMode.HTML,
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

    # Prepare latest draw info (HKJC API)
    latest = None
    api_data = fetch_hkjc_draws()
    draws = api_data.get("lotteryDraws") if api_data else None
    latest = get_latest_hkjc_draw(draws or [])
    next_draw_info = get_next_hkjc_draw(draws or [])

    if latest:
        date_str_raw = latest.get("drawDate", "") or ""
        try:
            date_str = datetime.fromisoformat(date_str_raw.replace("Z", "+00:00")).strftime(
                "%b %d, %Y"
            )
        except Exception:
            date_str = date_str_raw
        nums = latest.get("drawResult", {}).get("drawnNo") or []
        numbers_str = ", ".join(str(n) for n in nums)
        bonus = latest.get("drawResult", {}).get("xDrawnNo")
        last_draw_text = (
            "<b>Last Drawn Result:</b>\n"
            f"Date: {escape_html(date_str)} (Draw #{escape_html(latest.get('year',''))}/{escape_html(latest.get('no',''))})\n"
            f"Numbers: {escape_html(numbers_str)}\n"
            f"Extra:   {escape_html(bonus)}"
        )
        # Bubble 2: last drawn result
        await update.message.reply_text(last_draw_text, parse_mode=ParseMode.HTML)

    # Bubble 3: how to generate (with button attached)
    generate_text = (
        "Type /generate or\n"
        "Press the Generate button below for a unique combintaion"
    )
    await update.message.reply_text(generate_text, reply_markup=generate_keyboard())

    # Bubble 4: how to search
    search_text = (
        "Enter a combination of 6 numbers and check if it has been drawn\n"
        "<i>1, 26, 39, 47, 31, 50 etc.</i>"
    )
    await update.message.reply_text(search_text, parse_mode=ParseMode.HTML)

    # Bubble 5: next draw info (if available)
    if next_draw_info:
        draw_date_str = format_hkjc_dt(next_draw_info.get("drawDate", ""))
        close_date_str = format_hkjc_dt(next_draw_info.get("closeDate", ""))
        pool = next_draw_info.get("lotteryPool", {}) or {}
        est_first = format_currency(pool.get("derivedFirstPrizeDiv") or "")
        jackpot = format_currency(pool.get("jackpot") or "")
        next_draw_text = (
            "<b>Next Draw:</b>\n"
            f"<i>Date: {escape_html(draw_date_str)} (Draw #{escape_html(next_draw_info.get('year',''))}/{escape_html(next_draw_info.get('no',''))})</i>\n"
            f"<i>Sales close: {escape_html(close_date_str)}</i>\n"
            f"<i>Estimated 1st Division: HK${escape_html(est_first)}</i>\n"
            f"<i>Jackpot: HK${escape_html(jackpot)}</i>"
        )
        await update.message.reply_text(next_draw_text, parse_mode=ParseMode.HTML)


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
            numbers_str = ", ".join(str(n) for n in combo)
            await loading_msg.edit_text(
                f"Your unique combination is: <b>{escape_html(numbers_str)}</b>",
                parse_mode=ParseMode.HTML,
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
        numbers_str = ", ".join(str(n) for n in combo)
        await loading_msg.edit_text(
            f"Your unique combination is: <b>{escape_html(numbers_str)}</b>",
            parse_mode=ParseMode.HTML,
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
            "This combination <b>HAS</b> been drawn.\n"
            f"Date: {result['date']} (Draw #{result['draw_number']})\n"
            f"Numbers: {numbers_str}\n"
            f"Bonus: {result['bonus']}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await loading_msg.edit_text(
            "This combination has NEVER been drawn.\n"
            f"Numbers checked: {', '.join(str(n) for n in sorted(numbers))}"
        )

    # Keep generate button visible
    await send_generate_prompt(update, context)


async def nextdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    subscribe_chat(update, context)
    loading_msg = await update.message.reply_text("Loading...")
    data = fetch_hkjc_draws()
    if not data:
        await loading_msg.edit_text("Could not reach HKJC at the moment. Please try again.")
        await send_generate_prompt(update, context)
        return

    draws = data.get("lotteryDraws") or []
    next_draw = get_next_hkjc_draw(draws)
    if not next_draw:
        await loading_msg.edit_text("No next draw info available right now.")
        await send_generate_prompt(update, context)
        return

    draw_date_str = format_hkjc_dt(next_draw.get("drawDate", ""))
    close_date_str = format_hkjc_dt(next_draw.get("closeDate", ""))

    pool = next_draw.get("lotteryPool", {}) or {}
    est_first = format_currency(pool.get("derivedFirstPrizeDiv") or "")
    jackpot = format_currency(pool.get("jackpot") or "")
    unit = pool.get("unitBet") or 10

    msg = (
        "<b>Next Draw:</b>\n"
        f"<i>Date: {escape_html(draw_date_str)} (Draw #{escape_html(next_draw.get('year',''))}/{escape_html(next_draw.get('no',''))})</i>\n"
        f"<i>Sales close: {escape_html(close_date_str)}</i>\n"
        f"<i>Estimated 1st Division: HK${escape_html(est_first)} (unit bet HK${escape_html(unit)})</i>\n"
        f"<i>Jackpot: HK${escape_html(jackpot)}</i>"
    )
    await loading_msg.edit_text(msg, parse_mode=ParseMode.HTML)
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

    # Initialize last known draw number and reminders from HKJC API
    try:
        api_data = fetch_hkjc_draws()
        draws = api_data.get("lotteryDraws") if api_data else None
        latest = get_latest_hkjc_draw(draws or [])
        next_draw_init = get_next_hkjc_draw(draws or [])
        if latest:
            application.bot_data["last_draw_id"] = latest.get("id")
        if next_draw_init:
            application.bot_data["next_draw"] = next_draw_init
            application.bot_data.setdefault("reminders_sent", {})[
                next_draw_init.get("id")
            ] = set()
    except Exception:
        application.bot_data["last_draw_id"] = None

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("generate", generate_command))
    application.add_handler(CommandHandler("nextdraw", nextdraw_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, plain_text_handler))

    # Periodically check for new draws and notify subscribers
    job_queue: JobQueue = application.job_queue

    async def check_for_new_draw(context: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            api_data = fetch_hkjc_draws()
            draws = api_data.get("lotteryDraws") if api_data else None
        except Exception:
            return

        if not draws:
            return

        app = context.application
        latest = get_latest_hkjc_draw(draws)
        next_draw = get_next_hkjc_draw(draws)

        # New draw notification
        if latest:
            last_draw_id = app.bot_data.get("last_draw_id")
            current_id = latest.get("id")
            if current_id and current_id != last_draw_id:
                app.bot_data["last_draw_id"] = current_id
                subs: Set[int] = app.bot_data.get("subscribed_chats", set())
                date_str_raw = latest.get("drawDate", "") or ""
                try:
                    date_str = datetime.fromisoformat(
                        date_str_raw.replace("Z", "+00:00")
                    ).strftime("%b %d, %Y")
                except Exception:
                    date_str = date_str_raw
                nums = latest.get("drawResult", {}).get("drawnNo") or []
                numbers_str = ", ".join(str(n) for n in nums)
                bonus = latest.get("drawResult", {}).get("xDrawnNo")
                message = (
                    "New Mark 6 draw!\n"
                    f"Date: {date_str} (Draw #{latest.get('year','')}/{latest.get('no','')})\n"
                    f"Numbers: {numbers_str}\n"
                    f"Extra:   {bonus}"
                )
                for chat_id in subs:
                    try:
                        await context.bot.send_message(chat_id=chat_id, text=message)
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=get_generate_prompt_html(),
                            parse_mode=ParseMode.HTML,
                            reply_markup=generate_keyboard(),
                        )
                    except Exception:
                        continue

        # Store next draw info for reminders
        if next_draw:
            app.bot_data["next_draw"] = next_draw
            # Reset reminders when draw changes
            reminders = app.bot_data.setdefault("reminders_sent", {})
            if next_draw.get("id") not in reminders:
                reminders[next_draw.get("id")] = set()

            close_raw = next_draw.get("closeDate", "") or ""
            try:
                close_dt = datetime.fromisoformat(close_raw.replace("Z", "+00:00"))
            except Exception:
                close_dt = None

            if close_dt:
                now = datetime.now(close_dt.tzinfo)
                minutes_left = int((close_dt - now).total_seconds() // 60)
                sent_set = reminders.get(next_draw.get("id"), set())
                subs: Set[int] = app.bot_data.get("subscribed_chats", set())
                for thr in REMINDER_THRESHOLDS_MIN:
                    # Fire once per threshold when we are at or just inside the threshold window.
                    if minutes_left <= thr and thr not in sent_set:
                        pool = next_draw.get("lotteryPool", {}) or {}
                        est_first = format_currency(pool.get("derivedFirstPrizeDiv") or "")
                        jackpot = format_currency(pool.get("jackpot") or "")
                        close_display = format_hkjc_dt(next_draw.get("closeDate", ""))
                        msg = (
                            f"Reminder: {thr} minutes until Mark 6 draw closes.\n"
                            f"Draw #{next_draw.get('year','')}/{next_draw.get('no','')} "
                            f"closes at {close_display}.\n"
                            f"Estimated 1st Division: HK${est_first}\n"
                            f"Jackpot: HK${jackpot}"
                        )
                        for chat_id in subs:
                            try:
                                await context.bot.send_message(chat_id=chat_id, text=msg)
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=get_generate_prompt_html(),
                                    parse_mode=ParseMode.HTML,
                                    reply_markup=generate_keyboard(),
                                )
                            except Exception:
                                continue
                        sent_set.add(thr)
                reminders[next_draw.get("id")] = sent_set

    # Check frequently for new draws and reminders
    job_queue.run_repeating(check_for_new_draw, interval=60, first=5)

    application.run_polling()


if __name__ == "__main__":
    main()
