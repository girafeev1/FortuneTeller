import pandas as pd
import requests
from datetime import datetime

HKJC_GRAPHQL_URL = "https://info.cld.hkjc.com/graphql/base/"
DB_FILE = "merged_results.csv"
EXPECTED_COLUMNS = [
    "date",
    "draw_number",
    "num_1",
    "num_2",
    "num_3",
    "num_4",
    "num_5",
    "num_6",
    "bonus",
]


def fetch_hkjc_draws():
    """Fetch recent Mark Six draws from the official HKJC GraphQL endpoint."""
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
        existing_draw_numbers = set(db_df["draw_number"]) if not db_df.empty else set()
    except FileNotFoundError:
        db_df = pd.DataFrame()
        existing_draw_numbers = set()

    if not db_df.empty:
        db_df = db_df[[col for col in EXPECTED_COLUMNS if col in db_df.columns]].copy()
        if "draw_number" in db_df.columns:
            db_df = db_df[db_df["draw_number"].notna()]

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
        if draw_number in existing_draw_numbers:
            continue
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
        if db_df.empty:
            return
        combined_df = db_df.copy()
    else:
        latest_df = pd.DataFrame(records)
        # 4. Combine and remove duplicates
        combined_df = pd.concat([db_df, latest_df], ignore_index=True)
    for col in EXPECTED_COLUMNS:
        if col not in combined_df.columns:
            combined_df[col] = None
    combined_df = combined_df[EXPECTED_COLUMNS]
    combined_df.drop_duplicates(subset=["draw_number"], keep="first", inplace=True)

    # 5. Sort and save
    combined_df["date"] = pd.to_datetime(combined_df["date"], errors="coerce")
    combined_df = combined_df.sort_values(by="date", ascending=False, na_position="last")
    combined_df.to_csv(DB_FILE, index=False)

    print(f"Database updated successfully. Total records: {len(combined_df)}")


if __name__ == "__main__":
    update_database()
