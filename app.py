from flask import Flask, render_template, Response, request, jsonify
import json
import asyncio
import os
import sys

print("Starting app...", file=sys.stderr)

from core.scraper import run_all_tasks

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    app = Flask(__name__, template_folder=template_folder)
else:
    app = Flask(__name__)
EXCLUDED_FILE = 'excluded_stocks.json'

def load_excluded_list():
    if not os.path.exists(EXCLUDED_FILE):
        return []
    try:
        with open(EXCLUDED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_excluded_list(data):
    with open(EXCLUDED_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_stream_bridge():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    excluded_list = load_excluded_list()
    async_gen = run_all_tasks(excluded_list)
    
    while True:
        try:
            result = loop.run_until_complete(async_gen.__anext__())
            yield f"data: {json.dumps(result)}\n\n"
        except StopAsyncIteration:
            break
        except Exception:
            break
    yield "event: close\ndata: done\n\n"

@app.route('/stream_scrape')
def stream_scrape():
    return Response(generate_stream_bridge(), mimetype='text/event-stream')

@app.route('/')
def index():
    # 改用 render_template 讀取外部檔案
    return render_template('index.html')

@app.route('/api/excluded', methods=['GET'])
def get_excluded():
    return jsonify(load_excluded_list())

@app.route('/api/excluded', methods=['POST'])
def add_excluded():
    data = request.json
    code = data.get('code')
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    current_list = load_excluded_list()
    if code not in current_list:
        current_list.append(code)
        save_excluded_list(current_list)
    
    return jsonify(current_list)

@app.route('/api/excluded', methods=['DELETE'])
def remove_excluded():
    data = request.json
    code = data.get('code')
    if not code:
        return jsonify({'error': 'No code provided'}), 400
    
    current_list = load_excluded_list()
    if code in current_list:
        current_list.remove(code)
        save_excluded_list(current_list)
    
    return jsonify(current_list)

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
