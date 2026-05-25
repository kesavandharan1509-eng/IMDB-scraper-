
from flask import Flask, render_template, jsonify, send_file
import subprocess
import os
import csv
import webbrowser
from threading import Timer

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    csv_path = 'data/imdb_top250.csv'
    if os.path.exists(csv_path):
        data = []
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
        return jsonify({'success': True, 'data': data})
    else:
        return jsonify({'success': False, 'message': 'No data found. Please scrape first.'})

@app.route('/scrape', methods=['POST'])
def scrape():
    try:
        result = subprocess.run(['python', 'scraper.py', '--deep-limit', '0'], capture_output=True, text=True)
        
        csv_path = 'data/imdb_top250.csv'
        if os.path.exists(csv_path):
            data = []
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append(row)
                    
            return jsonify({
                'success': True,
                'message': 'Successfully scraped IMDb Top 250!',
                'data': data
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Scraping finished but CSV file not found. Log: ' + result.stdout
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@app.route('/download')
def download():
    path = "data/imdb_top250.csv"
    if os.path.exists(path):
        return send_file(path, as_attachment=True)
    return "File not found", 404

def open_browser():
    webbrowser.open_new('http://127.0.0.1:5000/')

if __name__ == '__main__':
    Timer(1.5, open_browser).start()
    app.run(debug=True, use_reloader=False)
