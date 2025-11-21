
from flask import Flask, render_template, request
import pandas as pd
import random

app = Flask(__name__)

def load_data():
    return pd.read_csv('merged_results.csv')

def generate_unique_combination(df):
    existing_combinations = set()
    for _, row in df.iterrows():
        combination = tuple(sorted([row['num_1'], row['num_2'], row['num_3'], row['num_4'], row['num_5'], row['num_6']]))
        existing_combinations.add(combination)

    while True:
        new_combination = tuple(sorted(random.sample(range(1, 50), 6)))
        if new_combination not in existing_combinations:
            return list(new_combination)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate')
def generate():
    df = load_data()
    new_combination = generate_unique_combination(df)
    return render_template('index.html', new_combination=new_combination)

@app.route('/search', methods=['POST'])
def search():
    df = load_data()
    
    try:
        numbers_str = request.form.get('numbers')
        numbers = sorted([int(n.strip()) for n in numbers_str.split(',')])
        if len(numbers) != 6:
            return render_template('index.html', error="Please enter exactly 6 numbers.")
    except (ValueError, AttributeError):
        return render_template('index.html', error="Invalid input. Please enter 6 comma-separated numbers.")

    search_combination = tuple(numbers)
    
    found = None
    for index, row in df.iterrows():
        combination = tuple(sorted([row['num_1'], row['num_2'], row['num_3'], row['num_4'], row['num_5'], row['num_6']]))
        if combination == search_combination:
            found = {
                'date': row['date'],
                'draw_number': row['draw_number'],
                'numbers': combination,
                'bonus': row['bonus']
            }
            break
            
    return render_template('index.html', search_result=found, searched_numbers=numbers)

if __name__ == '__main__':
    app.run(debug=True)
