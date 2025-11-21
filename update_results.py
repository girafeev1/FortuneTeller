
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
    
    # Find all year sections
    year_sections = soup.find_all('h2')

    for year_section in year_sections:
        year = year_section.text.strip()
        if not year.isdigit():
            continue

        # Find the table for the current year
        table = year_section.find_next('table', class_='table-striped')
        if not table:
            continue
            
        rows = table.find('tbody').find_all('tr')

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 3:
                continue

            draw_info = cols[0].text.strip().split('/')
            draw_year = year
            draw_number_in_year = draw_info[0]
            
            # Handle cases where draw number is YY/NNN
            if len(draw_info) > 1 and len(draw_info[0]) == 2:
                draw_year_short = draw_info[0]
                draw_number_in_year = draw_info[1]
            else:
                draw_year_short = str(year)[-2:]

            draw_number = f"{draw_year_short}/{draw_number_in_year}"

            if draw_number == last_draw_number:
                print(f"Found last known draw number: {last_draw_number}. Stopping.")
                return pd.DataFrame(results)
            
            date_str = cols[1].text.strip()
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d').strftime('%Y-%m-%d')
            except ValueError:
                # Handle different date formats if necessary
                date = None

            numbers_div = cols[2]
            numbers = [int(li.text) for li in numbers_div.find('ul', class_='list-inline').find_all('li', class_='result-ball')]
            bonus = int(numbers_div.find('li', class_='result-ball-extra').text)

            results.append({
                'draw_number': draw_number,
                'date': date,
                'num_1': numbers[0],
                'num_2': numbers[1],
                'num_3': numbers[2],
                'num_4': numbers[3],
                'num_5': numbers[4],
                'num_6': numbers[5],
                'bonus': bonus
            })
            
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
