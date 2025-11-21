import requests
import time

url = "https://tw.stock.yahoo.com/quote/2330"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"
}

print(f"Testing connection to {url}...")
try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Connection successful!")
        print("Preview (first 200 chars):")
        print(response.text[:200])
    else:
        print("Connection failed or blocked.")
except Exception as e:
    print(f"Error: {e}")
