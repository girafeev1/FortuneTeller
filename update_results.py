import pandas as pd
import requests
from datetime import datetime

HKJC_GRAPHQL_URL = "https://info.cld.hkjc.com/graphql/base/"
DB_FILE = "merged_results.csv"


def fetch_hkjc_draws():
    """Fetch recent Mark Six draws from the official HKJC GraphQL endpoint."""
    payload = {
        "operationName": "marksix",
        "variables": {},
        "query": (
            "fragment lotteryDrawsFragment on LotteryDraw {\n"
            "  id\n  year\n  no\n  openDate\n  closeDate\n  drawDate\n  status\n"
            "  lotteryPool { jackpot derivedFirstPrizeDiv }\n"
            "  drawResult { drawnNo xDrawnNo }\n"
            "}\n"
            "query marksix {\n"
            "  lotteryDraws { ...lotteryDrawsFragment }\n"
            "}\n"
        ),
    }
    try:
        res = requests.post(HKJC_GRAPHQL_URL, json=payload, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("data", {}).get("lotteryDraws") or []
    except Exception as e:
        print(f"Error fetching HKJC data: {e}")
        return []


def format_draw_number(year: str, no: int) -> str:
    year_short = str(year)[-2:]
    return f"{year_short}/{no}"


def update_database():
    # 1. Read the existing database and find the last draw number
    try:
        db_df = pd.read_csv(DB_FILE)
        last_draw_number = db_df["draw_number"].iloc[0] if not db_df.empty else None
    except FileNotFoundError:
        db_df = pd.DataFrame()
        last_draw_number = None

    # 2. Fetch draws from HKJC
    print("Fetching latest results from HKJC...")
    draws = fetch_hkjc_draws()

    if not draws:
        print("No data from HKJC. Aborting update.")
        return

    # 3. Build a dataframe for new results (only status=Result and not already in DB)
    records = []
    for d in draws:
        status = (d.get("status") or "").lower()
        if status != "result":
            continue
        draw_no = d.get("no")
        year = d.get("year")
        draw_number = format_draw_number(year, draw_no)
        if last_draw_number and draw_number == last_draw_number:
            # already up to date
            break
        draw_date_raw = d.get("drawDate", "") or ""
        try:
            draw_date = datetime.fromisoformat(draw_date_raw.replace("Z", "+00:00")).strftime(
                "%Y-%m-%d"
            )
        except Exception:
            draw_date = draw_date_raw
        nums = d.get("drawResult", {}).get("drawnNo") or []
        if len(nums) < 6:
            continue
        bonus = d.get("drawResult", {}).get("xDrawnNo")
        records.append(
            {
                "date": draw_date,
                "draw_number": draw_number,
                "num_1": nums[0],
                "num_2": nums[1],
                "num_3": nums[2],
                "num_4": nums[3],
                "num_5": nums[4],
                "num_6": nums[5],
                "bonus": bonus,
            }
        )

    if not records:
        print("No new results found.")
        return

    latest_df = pd.DataFrame(records)

    # 4. Combine and remove duplicates
    combined_df = pd.concat([db_df, latest_df], ignore_index=True)
    combined_df.drop_duplicates(subset=["draw_number"], keep="first", inplace=True)

    # 5. Sort and save
    combined_df["date"] = pd.to_datetime(combined_df["date"])
    combined_df = combined_df.sort_values(by="date", ascending=False)
    combined_df.to_csv(DB_FILE, index=False)

    print(f"Database updated successfully. Total records: {len(combined_df)}")


if __name__ == "__main__":
    update_database()

