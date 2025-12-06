
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime


def fetch_and_parse_lottery_hk(last_draw_number=None):
    url = "https://lottery.hk/en/mark-six/results/"
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    results = []

    # Current layout: a single results table with class "-center _results"
    table = soup.find("table", class_="-center _results")

    if not table:
        print("Could not find results table on lottery.hk page.")
        return pd.DataFrame(results)

    rows = table.find("tbody").find_all("tr")

    for row in rows:
        # Skip month header rows
        if "tshead" in row.get("class", []):
            continue

        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        # Draw number appears directly, e.g. "25/126"
        draw_number = cols[0].get_text(strip=True)

        if last_draw_number and draw_number == last_draw_number:
            print(f"Found last known draw number: {last_draw_number}. Stopping.")
            return pd.DataFrame(results)

        # Date is in format DD/MM/YYYY inside span.date
        date_span = cols[1].find("span", class_="date")
        date_str = date_span.get_text(strip=True) if date_span else cols[1].get_text(strip=True)

        date = None
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                date = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue

        # Numbers are inside ul.balls; last item (with "-plus") is bonus
        balls_ul = cols[2].find("ul", class_="balls")
        if not balls_ul:
            continue

        ball_items = balls_ul.find_all("li")
        if len(ball_items) < 7:
            # Expect 6 main numbers + 1 bonus
            continue

        ball_values = [int(li.get_text(strip=True)) for li in ball_items]
        numbers = ball_values[:-1]
        bonus = ball_values[-1]

        results.append(
            {
                "draw_number": draw_number,
                "date": date,
                "num_1": numbers[0],
                "num_2": numbers[1],
                "num_3": numbers[2],
                "num_4": numbers[3],
                "num_5": numbers[4],
                "num_6": numbers[5],
                "bonus": bonus,
            }
        )

    return pd.DataFrame(results)

def update_database():
    db_file = 'merged_results.csv'
    
    # 1. Read the existing database and find the last draw number
    try:
        db_df = pd.read_csv(db_file)
        last_draw_number = db_df['draw_number'].iloc[0] if not db_df.empty else None
    except FileNotFoundError:
        db_df = pd.DataFrame()
        last_draw_number = None

    # 2. Fetch the latest results from lottery.hk
    print("Fetching latest results from lottery.hk...")
    latest_df = fetch_and_parse_lottery_hk(last_draw_number)

    if latest_df is None or latest_df.empty:
        print("No new results found or could not fetch new results. Aborting update.")
        return

    # 3. Combine and remove duplicates
    combined_df = pd.concat([db_df, latest_df], ignore_index=True)
    combined_df.drop_duplicates(subset=['draw_number'], keep='last', inplace=True)

    # 4. Sort and save
    combined_df['date'] = pd.to_datetime(combined_df['date'])
    combined_df = combined_df.sort_values(by='date', ascending=False)
    combined_df.to_csv(db_file, index=False)

    print(f"Database updated successfully. Total records: {len(combined_df)}")

if __name__ == '__main__':
    update_database()
