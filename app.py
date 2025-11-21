from flask import Flask, jsonify, render_template
from flask_cors import CORS
import random
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Mock data for Taiwan stock futures
STOCK_FUTURES = [
    {'symbol': '2330', 'name': '台積電期貨', 'underlying': '台積電'},
    {'symbol': '2317', 'name': '鴻海期貨', 'underlying': '鴻海'},
    {'symbol': '2454', 'name': '聯發科期貨', 'underlying': '聯發科'},
    {'symbol': '2881', 'name': '富邦金期貨', 'underlying': '富邦金'},
    {'symbol': '2882', 'name': '國泰金期貨', 'underlying': '國泰金'},
    {'symbol': '2412', 'name': '中華電期貨', 'underlying': '中華電'},
    {'symbol': '2308', 'name': '台達電期貨', 'underlying': '台達電'},
    {'symbol': '2303', 'name': '聯電期貨', 'underlying': '聯電'},
]

# Base prices for mock data generation
BASE_PRICES = {
    '2330': 580.0,
    '2317': 105.0,
    '2454': 900.0,
    '2881': 68.0,
    '2882': 55.0,
    '2412': 125.0,
    '2308': 320.0,
    '2303': 48.0,
}

def generate_price_data(base_price):
    """Generate mock real-time price data"""
    change = random.uniform(-5, 5)
    change_percent = (change / base_price) * 100
    return {
        'price': round(base_price + change, 2),
        'change': round(change, 2),
        'change_percent': round(change_percent, 2),
        'volume': random.randint(1000, 50000),
        'high': round(base_price + random.uniform(0, 3), 2),
        'low': round(base_price - random.uniform(0, 3), 2),
        'open': round(base_price + random.uniform(-2, 2), 2),
    }

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return render_template('index.html')

@app.route('/api/futures')
def get_futures():
    """Get all stock futures with current data"""
    futures_data = []
    for future in STOCK_FUTURES:
        base_price = BASE_PRICES.get(future['symbol'], 100.0)
        price_data = generate_price_data(base_price)
        futures_data.append({
            **future,
            **price_data,
            'timestamp': datetime.now().isoformat()
        })
    
    return jsonify(futures_data)

@app.route('/api/futures/<symbol>')
def get_future_detail(symbol):
    """Get detailed information for a specific stock future"""
    future = next((f for f in STOCK_FUTURES if f['symbol'] == symbol), None)
    if not future:
        return jsonify({'error': 'Future not found'}), 404
    
    base_price = BASE_PRICES.get(symbol, 100.0)
    price_data = generate_price_data(base_price)
    
    return jsonify({
        **future,
        **price_data,
        'timestamp': datetime.now().isoformat(),
        'bid': round(price_data['price'] - 0.5, 2),
        'ask': round(price_data['price'] + 0.5, 2),
        'settlement': round(base_price, 2),
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
