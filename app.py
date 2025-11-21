from flask import Flask, render_template, Response
import json
import asyncio
from scraper import run_all_tasks

app = Flask(__name__)

def generate_stream_bridge():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    async_gen = run_all_tasks()
    
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

if __name__ == '__main__':
    app.run(debug=True, port=5000, threaded=True)
