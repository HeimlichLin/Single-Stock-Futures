import requests
import re

url = "https://tw.stock.yahoo.com/quote/2330"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36"}

try:
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        html = r.text
        print("Successfully fetched.")
        
        # Find "昨收" location
        indices = [m.start() for m in re.finditer('昨收', html)]
        for idx in indices:
            print(f"--- Context around index {idx} ---")
            print(html[idx:idx+200])
            print("-------------------------------")
    else:
        print(f"Failed with status {r.status_code}")
except Exception as e:
    print(f"Error: {e}")
