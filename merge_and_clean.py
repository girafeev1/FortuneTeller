
import pandas as pd
import re

def parse_csv_1(file_path):
    df = pd.read_csv(file_path, skiprows=1)
    df = df.dropna(how='all')
    df.rename(columns={'Bonus': 'Extra/ Bonus Number'}, inplace=True)
    return df

def parse_csv_2(file_path):
    df = pd.read_csv(file_path, skiprows=2)
    df = df.dropna(how='all')
    return df

def parse_md(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()

    data = []
    for line in lines:
        if line.startswith('-'):
            match = re.search(r'- ([\d\/]+) — ([\d\-]+) — Numbers: ([\d, ]+); Extra: (\d+)', line)
            if match:
                draw_number = match.group(1)
                date = match.group(2)
                numbers_str = match.group(3)
                extra = int(match.group(4))
                numbers = [int(n) for n in numbers_str.split(', ')]

                row = {
                    'Draw Date': date,
                    'Draw Number': draw_number,
                    '1st Number': numbers[0],
                    '2nd Number': numbers[1],
                    '3rd Number': numbers[2],
                    '4th Number': numbers[3],
                    '5th Number': numbers[4],
                    '6th Number': numbers[5],
                    'Extra/ Bonus Number': extra
                }
                data.append(row)

    df = pd.DataFrame(data)
    return df

def merge_and_clean():
    # File paths
    csv_file_1 = '/Users/gutchumi/Downloads/Historical Mark 6 Results - All (1).csv'
    csv_file_2 = '/Users/gutchumi/Downloads/Historical Mark 6 Results - All.csv'
    md_file = '/Users/gutchumi/mark6_results.md'
    output_file = '/Users/gutchumi/dev/mark6-generator/merged_results.csv'

    # Parse files
    df1 = parse_csv_1(csv_file_1)
    df2 = parse_csv_2(csv_file_2)
    df_md = parse_md(md_file)

    # Concatenate dataframes
    combined_df = pd.concat([df1, df2, df_md], ignore_index=True)

    # Data cleaning
    # Standardize column names
    combined_df.rename(columns={
        'Draw Date': 'date',
        'Draw Number': 'draw_number',
        '1st Number': 'num_1',
        '2nd Number': 'num_2',
        '3rd Number': 'num_3',
        '4th Number': 'num_4',
        '5th Number': 'num_5',
        '6th Number': 'num_6',
        'Extra/ Bonus Number': 'bonus'
    }, inplace=True)

    # Drop Total Turnover column if it exists
    if 'Total Turnover' in combined_df.columns:
        combined_df = combined_df.drop(columns=['Total Turnover'])

    # Remove duplicates based on draw_number
    combined_df = combined_df.drop_duplicates(subset=['draw_number'])

    # Convert date to datetime objects
    combined_df['date'] = pd.to_datetime(combined_df['date'], errors='coerce')

    # Remove rows with invalid dates
    combined_df = combined_df.dropna(subset=['date'])

    # Sort by date
    combined_df = combined_df.sort_values(by='date', ascending=False)

    # Convert number columns to integers
    num_cols = ['num_1', 'num_2', 'num_3', 'num_4', 'num_5', 'num_6', 'bonus']
    for col in num_cols:
        combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').astype('Int64')

    # Save to CSV
    combined_df.to_csv(output_file, index=False)
    print(f"Merged and cleaned data saved to {output_file}")

if __name__ == '__main__':
    merge_and_clean()
